import { Link } from 'react-router-dom';
import './Landing.css';

const features = [
  { icon: '🧠', title: 'Structured Reasoning',   desc: 'Chain-of-Thought decomposition breaks your topic into key concepts and subtopics with beginner-friendly explanations.' },
  { icon: '📚', title: 'Live Paper Search',       desc: 'Searches ArXiv in real-time to find the most relevant research papers published in your domain.' },
  { icon: '🔍', title: 'Gap Analysis',            desc: 'Uses RAG to analyze papers and pinpoint limitations, unresolved questions, and open research problems.' },
  { icon: '💡', title: 'Hypothesis Generation',   desc: 'Generates 3 novel, testable hypotheses grounded in the literature with experiment setups and novelty scores.' },
  { icon: '∑',  title: 'Math Formulation',        desc: 'Translates your research idea into a formal optimization or statistical problem with LaTeX equations.' },
  { icon: '🗺️', title: 'Beginner Roadmap',        desc: 'Week-by-week learning plan from zero to research-ready, with tasks, resources, and milestones.' },
];

export default function Landing() {
  return (
    <div className="landing">
      {/* Nav */}
      <nav className="landing-nav">
        <div className="nav-logo">
          <div className="nav-logo-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="var(--choc)" opacity="0.9"/>
              <path d="M2 17l10 5 10-5" stroke="var(--choc)" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M2 12l10 5 10-5" stroke="var(--choc-light)" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <span style={{ fontWeight: 800, color: 'var(--choc)', letterSpacing: '-0.02em' }}>SciGenAI</span>
        </div>
        <div className="nav-actions">
          <Link to="/login" className="btn btn-ghost">Sign in</Link>
          <Link to="/register" className="btn btn-primary">Get Started →</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-badge">
          <span className="pulse-dot" />
          Powered by Gemini · LangGraph · RAG
        </div>
        <h1>
          Your AI
          <br />
          <span className="gradient-text">Research Co-Pilot</span>
        </h1>
        <p className="hero-sub">
          Type any research topic or problem statement. Get a complete, structured research blueprint —
          papers, gaps, hypotheses, math formulations, and a step-by-step learning roadmap. Built for beginners.
        </p>
        <div className="hero-cta">
          <Link to="/register" className="btn btn-primary" style={{ padding: '14px 32px', fontSize: '1rem' }}>
            Start Researching for Free →
          </Link>
          <Link to="/login" className="btn btn-ghost" style={{ padding: '14px 24px', fontSize: '0.95rem' }}>
            Already have an account
          </Link>
        </div>
        <div className="hero-demo glass">
          <div className="demo-label">Example input</div>
          <div className="demo-query">"Graph Neural Networks for drug discovery in oncology"</div>
          <div className="demo-steps">
            {['Reasoning', 'ArXiv Search', 'Gap Analysis', 'Hypothesis', 'Math', 'Roadmap'].map((s, i) => (
              <span key={i} className="demo-step badge badge-purple">{s}</span>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features">
        <h2 className="section-title">Everything a beginner researcher needs</h2>
        <p className="section-sub">Six AI-powered modules in one seamless pipeline</p>
        <div className="features-grid">
          {features.map((f, i) => (
            <div key={i} className="feature-card fade-in" style={{ animationDelay: `${i * 0.07}s` }}>
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>Built with Gemini · LangGraph · FastAPI · React</p>
      </footer>
    </div>
  );
}
