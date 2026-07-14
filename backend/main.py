"""
main.py – FastAPI application entry point.
Provides all REST API endpoints for auth and the research pipeline.
"""

import json
import asyncio
import os
import logging
import uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from jose import JWTError, jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import get_db, init_db, User, ResearchSession
from schemas import (
    UserCreate, UserLogin, Token,
    ResearchRequest, ResearchBlueprint, SessionSummary
)
from auth import hash_password, verify_password, create_access_token, get_current_user, SECRET_KEY, ALGORITHM
from agents.agent_graph import run_pipeline

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_assistant")

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Server shutting down.")


app = FastAPI(
    title="Research Assistant API",
    description="GenAI-powered research assistant for beginners",
    version="1.0.0",
    lifespan=lifespan,
    # Disable /docs and /redoc in production if desired
    # docs_url=None, redoc_url=None,
)

# Attach rate-limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
)
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "Research Assistant API is running"}


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.post("/api/auth/register", response_model=Token)
@limiter.limit("10/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    if not payload.username or len(payload.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = User(
        username=payload.username.strip(),
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email})
    logger.info(f"New user registered: {user.username}")
    return {"access_token": token, "token_type": "bearer", "username": user.username}


@app.post("/api/auth/login", response_model=Token)
@limiter.limit("20/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})
    logger.info(f"User logged in: {user.username}")
    return {"access_token": token, "token_type": "bearer", "username": user.username}


@app.post("/api/auth/guest", response_model=Token)
@limiter.limit("20/minute")
def guest_login(request: Request, db: Session = Depends(get_db)):
    guest_id = str(uuid.uuid4())[:8]
    username = f"Guest_{guest_id}"
    email = f"guest_{guest_id}@example.com"
    password = str(uuid.uuid4())

    # Use an extremely fast hash for guests to prevent CPU blocking on Render
    import bcrypt
    fast_salt = bcrypt.gensalt(rounds=4)
    fast_hash = bcrypt.hashpw(password.encode('utf-8'), fast_salt).decode('utf-8')

    user = User(
        username=username,
        email=email,
        hashed_password=fast_hash,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email})
    logger.info(f"Guest user registered/logged in: {user.username}")
    return {"access_token": token, "token_type": "bearer", "username": user.username}


# ── Research Routes ───────────────────────────────────────────────────────────
@app.get("/api/research/stream")
@limiter.limit("3/minute")
async def stream_research(
    request: Request,
    topic: str,
    token: str,
    db: Session = Depends(get_db),
):
    """SSE endpoint: streams step progress then emits the final blueprint."""
    # Validate token manually (EventSource cannot send Authorization headers)
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

    topic = topic.strip()
    if not topic or len(topic) < 5:
        raise HTTPException(status_code=400, detail="Topic must be at least 5 characters")
    if len(topic) > 500:
        raise HTTPException(status_code=400, detail="Topic must be under 500 characters")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_step(step: int, label: str):
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "step", "step": step, "label": label})

    def run_in_thread():
        try:
            result = run_pipeline(topic, on_step=on_step)
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done", "data": result})
        except Exception as e:
            logger.error(f"Pipeline error for topic '{topic}': {e}")
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
                    topic=topic,
                    blueprint_json=json.dumps(blueprint),
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                logger.info(f"Blueprint saved: session_id={session.id} user={current_user.username}")
                payload_out = {"type": "done", "session_id": session.id, **blueprint}
                yield f"data: {json.dumps(payload_out)}\n\n"
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
    logger.info(f"Session {session_id} deleted by user {current_user.username}")
    return {"message": "Session deleted"}


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
