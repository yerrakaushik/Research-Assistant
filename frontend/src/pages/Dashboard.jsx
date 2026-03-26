import { useState, useRef } from 'react';
import toast from 'react-hot-toast';
import Sidebar from '../components/Sidebar';
import BlueprintView from '../components/BlueprintView';
import './Dashboard.css';

const PIPELINE_STEPS = [
  { id: 1, label: 'Structured Reasoning',  icon: '🧠' },
  { id: 2, label: 'ArXiv Paper Search',    icon: '📚' },
  { id: 3, label: 'RAG Gap Analysis',      icon: '🔍' },
  { id: 4, label: 'Hypothesis Generation', icon: '💡' },
  { id: 5, label: 'Math Formulation',      icon: '∑'  },
  { id: 6, label: 'Roadmap Generation',    icon: '🗺️' },
  { id: 7, label: 'Critic Validation',     icon: '✅' },
];

const EXAMPLES = [
  'Graph Neural Networks for drug discovery',
  'Federated learning for healthcare privacy',
  'Vision transformers vs CNNs for medical imaging',
];

export default function Dashboard() {
  const [topic, setTopic] = useState('');
  const [blueprint, setBlueprint] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState([]);
  const sidebarRef = useRef(null);

  // Three view states: 'home' | 'loading' | 'result'
  const view = loading ? 'loading' : blueprint ? 'result' : 'home';

  const handleRun = async (e) => {
    e?.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    setBlueprint(null);
    setCurrentStep(0);
    setCompletedSteps([]);

    const token = localStorage.getItem('token');
    const url = `http://localhost:8000/api/research/stream?topic=${encodeURIComponent(topic.trim())}&token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'step') {
        setCompletedSteps((prev) => {
          const next = [...prev];
          if (msg.step > 1 && !next.includes(msg.step - 1)) next.push(msg.step - 1);
          return next;
        });
        setCurrentStep(msg.step);
      } else if (msg.type === 'done') {
        es.close();
        setCompletedSteps(PIPELINE_STEPS.map((s) => s.id));
        setCurrentStep(0);
        const { type, session_id, ...blueprintData } = msg;
        setBlueprint(blueprintData);
        setActiveSessionId(session_id);
        setLoading(false);
        toast.success('Research blueprint ready!');
        if (sidebarRef.current) sidebarRef.current.reload();
      } else if (msg.type === 'error') {
        es.close();
        setLoading(false);
        setCurrentStep(0);
        toast.error(msg.message || 'Pipeline failed. Check your API key.');
      }
    };

    es.onerror = () => {
      es.close();
      setLoading(false);
      setCurrentStep(0);
      toast.error('Connection lost. Please try again.');
    };
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); handleRun(); }
  };

  const handleSelectSession = (data, id) => {
    setBlueprint(data);
    setActiveSessionId(id);
    setTopic(data.topic);
  };

  const handleNewResearch = () => {
    setBlueprint(null);
    setActiveSessionId(null);
    setTopic('');
    setCurrentStep(0);
    setCompletedSteps([]);
  };

  return (
    <div className="dashboard-layout">
      <Sidebar
        ref={sidebarRef}
        onSelect={handleSelectSession}
        activeId={activeSessionId}
        onNewResearch={handleNewResearch}
      />

      <main className="dashboard-main">

        {/* ── HOME: centered search ── */}
        {view === 'home' && (
          <div className="home-view fade-in">
            <div className="home-hero">
              <div className="home-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" fill="var(--choc)" opacity="0.85"/>
                  <path d="M2 17l10 5 10-5" stroke="var(--choc)" strokeWidth="1.5" strokeLinecap="round"/>
                  <path d="M2 12l10 5 10-5" stroke="var(--choc-light)" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
              <h1 className="home-title">Start your research</h1>
              <p className="home-sub">Enter any topic and SciGenAI will generate a complete research blueprint — papers, gaps, hypotheses, math, and a learning roadmap.</p>
            </div>

            <form className="home-search-bar" onSubmit={handleRun}>
              <div className="home-search-icon">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
                </svg>
              </div>
              <input
                autoFocus
                type="text"
                className="home-search-input"
                placeholder="e.g. 'Vision Transformers for medical image segmentation'"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button type="submit" className="home-search-btn" disabled={!topic.trim()}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
                Generate
              </button>
            </form>

            <div className="home-examples">
              <span className="examples-label">Try an example</span>
              <div className="examples-row">
                {EXAMPLES.map((t, i) => (
                  <button key={i} className="example-chip" onClick={() => setTopic(t)}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── LOADING: pipeline progress ── */}
        {view === 'loading' && (
          <div className="loading-view fade-in">
            <div className="pipeline-progress">
              <div className="progress-header">
                <div className="progress-title">
                  <span className="progress-dot" />
                  Generating blueprint for "{topic}"
                </div>
                <span className="progress-hint">60–120 seconds</span>
              </div>
              <div className="progress-steps">
                {PIPELINE_STEPS.map((step) => {
                  const isDone = completedSteps.includes(step.id);
                  const isActive = currentStep === step.id;
                  const status = isDone ? 'done' : isActive ? 'active' : '';
                  return (
                    <div key={step.id} className={`progress-step ${status}`}>
                      <div className="step-icon">
                        {isDone
                          ? <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>
                          : isActive
                          ? <span className="spinner" style={{ width: 11, height: 11, borderWidth: 2 }} />
                          : <span>{step.id}</span>}
                      </div>
                      <span className="step-emoji">{step.icon}</span>
                      {step.label}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── RESULT: blueprint ── */}
        {view === 'result' && (
          <div className="result-view fade-in">
            <BlueprintView blueprint={blueprint} />
          </div>
        )}

      </main>
    </div>
  );
}
