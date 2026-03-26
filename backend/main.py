"""
main.py – FastAPI application entry point.
Provides all REST API endpoints for auth and the research pipeline.
"""

import json
import asyncio
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse 
from sqlalchemy.orm import Session
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from database import get_db, init_db, User, ResearchSession
from schemas import (
    UserCreate, UserLogin, Token,
    ResearchRequest, ResearchBlueprint, SessionSummary
)
from auth import hash_password, verify_password, create_access_token, get_current_user
from agents.agent_graph import run_pipeline

app = FastAPI(
    title="Research Assistant API",
    description="GenAI-powered research assistant for beginners",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:3000", "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    print("[Server] Database initialized.")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "Research Assistant API is running"}


# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.post("/api/auth/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "username": user.username}


@app.post("/api/auth/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "username": user.username}


# ── Research Routes ───────────────────────────────────────────────────────────
@app.post("/api/research")
def run_research(
    request: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Runs the full 6-step research pipeline and saves the result."""
    if not request.topic or len(request.topic.strip()) < 5:
        raise HTTPException(status_code=400, detail="Topic must be at least 5 characters")

    blueprint = run_pipeline(request.topic.strip())

    session = ResearchSession(
        user_id=current_user.id,
        topic=request.topic.strip(),
        blueprint_json=json.dumps(blueprint),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {"session_id": session.id, **blueprint}


@app.get("/api/research/stream")
async def stream_research(
    topic: str,
    token: str,
    db: Session = Depends(get_db),
):
    """SSE endpoint: streams step progress then emits the final blueprint."""
    from auth import get_current_user as _get_user
    from fastapi.security import OAuth2PasswordBearer
    # Validate token manually since EventSource can't send headers
    from jose import JWTError, jwt
    from auth import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    current_user = db.query(User).filter(User.email == email).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    if not topic or len(topic.strip()) < 5:
        raise HTTPException(status_code=400, detail="Topic must be at least 5 characters")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_step(step: int, label: str):
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "step", "step": step, "label": label})

    def run_in_thread():
        try:
            result = run_pipeline(topic.strip(), on_step=on_step)
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done", "data": result})
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})

    executor = ThreadPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, run_in_thread)

    async def event_generator():
        while True:
            msg = await queue.get()
            if msg["type"] == "step":
                yield f"data: {json.dumps(msg)}\n\n"
            elif msg["type"] == "done":
                blueprint = msg["data"]
                session = ResearchSession(
                    user_id=current_user.id,
                    topic=topic.strip(),
                    blueprint_json=json.dumps(blueprint),
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                payload = {"type": "done", "session_id": session.id, **blueprint}
                yield f"data: {json.dumps(payload)}\n\n"
                break
            elif msg["type"] == "error":
                yield f"data: {json.dumps(msg)}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns a list of past research sessions for the current user."""
    sessions = (
        db.query(ResearchSession)
        .filter(ResearchSession.user_id == current_user.id)
        .order_by(ResearchSession.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {"id": s.id, "topic": s.topic, "created_at": s.created_at.isoformat()}
        for s in sessions
    ]


@app.get("/api/blueprint/{session_id}")
def get_blueprint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the saved blueprint for a specific session."""
    session = db.query(ResearchSession).filter(
        ResearchSession.id == session_id,
        ResearchSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    blueprint = json.loads(session.blueprint_json)
    return {"session_id": session.id, "created_at": session.created_at.isoformat(), **blueprint}


@app.delete("/api/blueprint/{session_id}")
def delete_blueprint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes a saved session."""
    session = db.query(ResearchSession).filter(
        ResearchSession.id == session_id,
        ResearchSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
