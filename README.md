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

## 🚀 Deployment

### 1. Backend (Render)
This project is configured for one-click deployment on Render using the `render.yaml` blueprint.
1. Create a [Render](https://render.com/) account.
2. Connect your GitHub repository.
3. Render will detect `render.yaml` and prompt to create the Blueprint.
4. Set the following Environment Variables in the Render dashboard:
   - `GEMINI_API_KEY`: Your key from Google AI Studio.
   - `ALLOWED_ORIGINS`: Set this to your Vercel URL once the frontend is deployed.

### 2. Frontend (Vercel)
1. Import your repository into [Vercel](https://vercel.com/).
2. Set the **Root Directory** to `frontend`.
3. Add an Environment Variable:
   - `VITE_API_URL`: The URL of your Render backend (e.g., `https://research-assistant-api.onrender.com`).
4. Deploy!

## 🐳 Docker (Local Development)
You can run the entire stack locally using Docker:
```bash
docker-compose up --build
```
The backend will be available at `localhost:8000` and the frontend at `localhost:5173`.

## 📜 License
MIT
