import { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { getHistory, getBlueprint, deleteBlueprint } from '../utils/api';
import './Sidebar.css';

const Sidebar = forwardRef(function Sidebar({ onSelect, activeId, onNewResearch }, ref) {
  const [history, setHistory] = useState([]);
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const username = localStorage.getItem('username') || 'Researcher';

  useImperativeHandle(ref, () => ({ reload: loadHistory }));
  useEffect(() => { loadHistory(); }, []);

  const loadHistory = async () => {
    try { const res = await getHistory(); setHistory(res.data); } catch {}
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
    toast.success('Logged out');
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await deleteBlueprint(id);
      setHistory((h) => h.filter((s) => s.id !== id));
      if (activeId === id) onNewResearch();
      toast.success('Session deleted');
    } catch { toast.error('Failed to delete'); }
  };

  const handleSelect = async (id) => {
    try { const res = await getBlueprint(id); onSelect(res.data, id); }
    catch { toast.error('Failed to load session'); }
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Header */}
      <div className="sidebar-header">
        {!collapsed && (
          <div className="sidebar-logo">
            <div className="logo-mark">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5z" fill="var(--choc)" opacity="0.9"/>
                <path d="M2 17l10 5 10-5" stroke="var(--choc)" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M2 12l10 5 10-5" stroke="var(--choc-light)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <span className="logo-name">SciGenAI</span>
          </div>
        )}
        <button
          className="collapse-btn"
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6"/>
            </svg>
          )}
        </button>
      </div>

      {/* New Research */}
      {!collapsed && (
        <button className="new-research-btn" onClick={onNewResearch}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          New Research
        </button>
      )}
      {collapsed && (
        <button className="new-research-btn-icon" onClick={onNewResearch} title="New Research">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </button>
      )}

      {/* History */}
      {!collapsed && (
        <div className="sidebar-history">
          <div className="sidebar-section-label">Recent Sessions</div>
          {history.length === 0 ? (
            <div className="no-history">No sessions yet. Start your first research!</div>
          ) : (
            history.map((s) => (
              <div
                key={s.id}
                className={`history-item ${activeId === s.id ? 'active' : ''}`}
                onClick={() => handleSelect(s.id)}
              >
                <div className="history-topic">{s.topic}</div>
                <div className="history-meta">
                  {new Date(s.created_at).toLocaleDateString()}
                  <button className="del-btn" onClick={(e) => handleDelete(e, s.id)} title="Delete">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Footer */}
      <div className="sidebar-footer">
        {!collapsed ? (
          <>
            <div className="user-info">
              <div className="user-avatar">{username[0].toUpperCase()}</div>
              <div>
                <div className="user-name">{username}</div>
                <div className="user-role">Researcher</div>
              </div>
            </div>
            <button className="logout-btn" onClick={handleLogout}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
              </svg>
              Sign Out
            </button>
          </>
        ) : (
          <button className="logout-btn-icon" onClick={handleLogout} title="Sign Out">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
            </svg>
          </button>
        )}
      </div>
    </aside>
  );
});

export default Sidebar;
