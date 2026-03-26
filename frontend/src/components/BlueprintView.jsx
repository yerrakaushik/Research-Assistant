import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import html2pdf from 'html2pdf.js';
import './BlueprintView.css';

const TABS = [
  { id: 'reasoning', label: '🧠 Reasoning', icon: '🧠' },
  { id: 'papers', label: '📚 Papers', icon: '📚' },
  { id: 'hypothesis', label: '💡 Hypotheses', icon: '💡' },
  { id: 'math', label: '∑ Math', icon: '∑' },
  { id: 'roadmap', label: '🗺️ Roadmap', icon: '🗺️' },
];

export default function BlueprintView({ blueprint }) {
  const [activeTab, setActiveTab] = useState('reasoning');

  if (!blueprint) return null;

  return (
    <div className="blueprint fade-in">
      <div className="blueprint-header">
        <h2 className="gradient-text">{blueprint.topic}</h2>
        <div className="blueprint-meta">
          <span className="badge badge-purple">✓ Blueprint Ready</span>
          <span className="badge badge-cyan">{blueprint.papers?.length || 0} Papers</span>
          <span className="badge badge-green">{blueprint.hypotheses?.length || 0} Hypotheses</span>
          {blueprint.critic_scores && (
            <span
              className="badge badge-amber"
              title={Object.entries(blueprint.critic_scores).map(([k, v]) => `${k}: ${v}/10`).join(' · ')}
            >
              🎯 Quality: {Math.round(Object.values(blueprint.critic_scores).reduce((a, b) => a + b, 0) / Object.values(blueprint.critic_scores).length)}/10
            </span>
          )}
        </div>
      </div>

      {/* Tab Bar */}
      <div className="tab-bar">
        {TABS.map((t) => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'reasoning' && <ReasoningTab data={blueprint.reasoning} />}
        {activeTab === 'papers' && <PapersTab papers={blueprint.papers} gaps={blueprint.gaps} />}
        {activeTab === 'hypothesis' && <HypothesisTab hypotheses={blueprint.hypotheses} />}
        {activeTab === 'math' && <MathTab math={blueprint.math_formulation} />}
        {activeTab === 'roadmap' && <RoadmapTab roadmap={blueprint.roadmap} />}
      </div>
    </div>
  );
}

/* ── Tab Components ─────────────────────────────────────────────────────── */
function ReasoningTab({ data }) {
  if (!data) return <Empty />;
  return (
    <div className="tab-pane fade-in">
      <div className="reasoning-summary glass">{data.summary}</div>
      <div className="two-col">
        <div>
          <SectionTitle>Key Subtopics</SectionTitle>
          <ul className="topic-list">
            {data.subtopics?.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
        <div>
          <SectionTitle>Key Concepts to Learn</SectionTitle>
          <div className="concept-tags">
            {data.key_concepts?.map((c, i) => <span key={i} className="badge badge-cyan">{c}</span>)}
          </div>
        </div>
      </div>
      <div className="difficulty-block glass">
        <span className="badge badge-amber">Difficulty: {data.difficulty_level}</span>
        <p style={{ marginTop: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>{data.explanation}</p>
      </div>
    </div>
  );
}

function PapersTab({ papers, gaps }) {
  const yearCounts = papers?.reduce((acc, p) => {
    const year = p.published?.substring(0, 4);
    if (year && year !== 'Unkn') {
      acc[year] = (acc[year] || 0) + 1;
    }
    return acc;
  }, {});
  const chartData = Object.keys(yearCounts || {}).sort().map(y => ({ year: y, count: yearCounts[y] }));

  return (
    <div className="tab-pane fade-in">
      {gaps?.length > 0 && (
        <>
          <SectionTitle>Research Gaps Identified</SectionTitle>
          <ul className="gap-list">
            {gaps.map((g, i) => <li key={i} className="gap-item">{g}</li>)}
          </ul>
        </>
      )}

      {chartData.length > 0 && (
        <>
          <SectionTitle>Publication Trend Analysis</SectionTitle>
          <div className="glass" style={{ height: 220, padding: '20px 20px 10px 0', marginBottom: 24, borderRadius: '12px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} tickMargin={10} axisLine={false} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} axisLine={false} tickLine={false} />
                <Tooltip 
                  cursor={{ fill: 'rgba(124, 58, 237, 0.1)' }} 
                  contentStyle={{ background: '#0d0d14', border: '1px solid #7c3aed', borderRadius: '8px', fontSize: '0.85rem' }} 
                />
                <Bar dataKey="count" fill="url(#colorAccent)" radius={[4, 4, 0, 0]} barSize={36} />
                <defs>
                  <linearGradient id="colorAccent" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#a855f7" stopOpacity={1}/>
                    <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.8}/>
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      <SectionTitle>Papers Found ({papers?.length || 0})</SectionTitle>
      <div className="papers-grid">
        {papers?.map((p, i) => (
          <a key={i} href={p.url} target="_blank" rel="noopener noreferrer" className="paper-card glass">
            <div className="paper-header">
              <span className="badge badge-purple">#{i + 1}</span>
              <span className="paper-date">{p.published}</span>
            </div>
            <h3 className="paper-title">{p.title}</h3>
            <div className="paper-authors">{p.authors?.join(', ')}</div>
            <p className="paper-abstract">{p.abstract?.slice(0, 260)}…</p>
            <div className="paper-link">View on ArXiv →</div>
          </a>
        ))}
      </div>
    </div>
  );
}

function HypothesisTab({ hypotheses }) {
  if (!hypotheses?.length) return <Empty />;
  return (
    <div className="tab-pane fade-in">
      <SectionTitle>{hypotheses.length} Novel Hypotheses Generated</SectionTitle>
      {hypotheses.map((h, i) => (
        <div key={i} className="hyp-card glass">
          <div className="hyp-header">
            <span className="hyp-num">{i + 1}</span>
            <h3>{h.title}</h3>
            <span className="badge badge-green">Novelty {h.novelty_score}/10</span>
          </div>
          <div className="hyp-body">
            <HypSection label="💬 Rationale" text={h.rationale} />
            <HypSection label="🧪 Experiment Setup" text={h.experiment_setup} />
            <HypSection label="📈 Expected Outcome" text={h.expected_outcome} />
          </div>
        </div>
      ))}
    </div>
  );
}

function MathTab({ math }) {
  if (!math) return <Empty />;
  return (
    <div className="tab-pane fade-in">
      <div className="math-header glass">
        <span className="badge badge-purple">{math.problem_type}</span>
        <div className="math-equation">
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
            {`$$${math.latex}$$`}
          </ReactMarkdown>
        </div>
      </div>
      <div className="two-col" style={{ marginTop: 20 }}>
        <div>
          <SectionTitle>📌 Objective</SectionTitle>
          <p className="math-text">{stripLatex(math.objective)}</p>
          <SectionTitle style={{ marginTop: 16 }}>⚙️ Algorithm Suggestion</SectionTitle>
          <p className="math-text">{stripLatex(math.algorithm_suggestion)}</p>
        </div>
        <div>
          <SectionTitle>🔢 Decision Variables</SectionTitle>
          <ul className="var-list">
            {math.variables?.map((v, i) => <li key={i}><code>{stripLatex(v)}</code></li>)}
          </ul>
          <SectionTitle style={{ marginTop: 16 }}>📐 Constraints</SectionTitle>
          <ul className="var-list">
            {math.constraints?.map((c, i) => <li key={i}>{stripLatex(c)}</li>)}
          </ul>
        </div>
      </div>
    </div>
  );
}

function RoadmapTab({ roadmap }) {
  if (!roadmap?.length) return <Empty />;

  const handleDownload = () => {
    const element = document.getElementById('roadmap-printable');
    const opt = {
      margin: 15,
      filename: 'Research_Roadmap.pdf',
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, backgroundColor: '#0d0d14' },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(element).save();
  };

  return (
    <div className="tab-pane fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <SectionTitle style={{ marginBottom: 0 }}>📅 {roadmap.length}-Week Research Roadmap</SectionTitle>
        <button className="btn btn-ghost" onClick={handleDownload} style={{ padding: '6px 16px', fontSize: '0.8rem' }}>
          📄 Download PDF
        </button>
      </div>
      <div className="roadmap-timeline" id="roadmap-printable" style={{ padding: '10px 0' }}>
        {roadmap.map((week, i) => (
          <div key={i} className="roadmap-week">
            <div className="week-marker">
              <div className="week-dot" />
              {i < roadmap.length - 1 && <div className="week-line" />}
            </div>
            <div className="week-content glass">
              <div className="week-header">
                <span className="badge badge-purple">Week {week.week}</span>
                <span className="week-goal">{week.goal}</span>
              </div>
              <div className="week-grid">
                <div>
                  <div className="week-label">Topics</div>
                  <ul className="week-list">{week.topics?.map((t, j) => <li key={j}>{t}</li>)}</ul>
                </div>
                <div>
                  <div className="week-label">Tasks</div>
                  <ul className="week-list">{week.tasks?.map((t, j) => <li key={j}>✓ {t}</li>)}</ul>
                </div>
                <div>
                  <div className="week-label">Resources</div>
                  <ul className="week-list">{week.resources?.map((r, j) => <li key={j}>📖 {r}</li>)}</ul>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function stripLatex(text) {
  if (!text) return '';
  return text
    .replace(/\$\$[\s\S]*?\$\$/g, '')       // remove block math $$...$$
    .replace(/\$[^$]*?\$/g, '')              // remove inline math $...$
    .replace(/\\[a-zA-Z]+\{([^}]*)\}/g, '$1') // \cmd{content} → content
    .replace(/\\[a-zA-Z]+/g, '')             // remove bare \commands
    .replace(/[{}]/g, '')                    // remove stray braces
    .replace(/\s{2,}/g, ' ')                 // collapse extra spaces
    .trim();
}
function SectionTitle({ children, style }) {
  return <div className="section-title-sm" style={style}>{children}</div>;
}
function HypSection({ label, text }) {
  return (
    <div className="hyp-section">
      <div className="hyp-label">{label}</div>
      <p>{text}</p>
    </div>
  );
}
function Empty() {
  return <div className="empty-state">No data generated for this section.</div>;
}
