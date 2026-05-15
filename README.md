# ⚗️ Research Assistant – AI Research Co-Pilot

> A Generative AI–powered research assistant for beginners. Enter any topic and get a complete, structured research blueprint.

## Stack
- **Backend**: FastAPI · LangGraph · Google Gemini 1.5 Flash · ArXiv · FAISS RAG · SQLite
- **Frontend**: React 18 · Vite · Vanilla CSS (dark glassmorphism) · KaTeX

## Project Structure
```
Researcher Assistant/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── auth.py              # JWT auth
│   ├── database.py          # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── agents/
│   │   ├── agent_graph.py   # LangGraph pipeline
│   │   ├── arxiv_search.py  # ArXiv paper search
│   │   ├── rag_engine.py    # FAISS RAG
│   │   ├── reasoning_chain.py
│   │   ├── hypothesis_gen.py
│   │   ├── math_formulation.py
│   │   └── roadmap_gen.py
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/           # Landing, Login, Register, Dashboard
        └── components/      # Sidebar, BlueprintView
```

## Setup

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Copy .env.example to .env and add your Gemini API key
copy .env.example .env
# Edit .env: GEMINI_API_KEY=your_key_here

python main.py                 # Runs on http://localhost:8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev                    # Runs on http://localhost:5173
```

## Pipeline Flow
```
User Topic
    ↓
① Chain-of-Thought Reasoning     (Gemini)
    ↓
② ArXiv Paper Search             (arxiv library)
    ↓
③ RAG Gap Analysis               (FAISS + sentence-transformers)
    ↓
④ Hypothesis Generation          (Gemini + RAG context)
    ↓
⑤ Math Formulation               (Gemini → LaTeX)
    ↓
⑥ Beginner Roadmap               (Gemini)
    ↓
📄 Research Blueprint
```

## Get a Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add to `backend/.env` as `GEMINI_API_KEY=...`
