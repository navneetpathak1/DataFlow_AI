import React, { useState, useEffect } from 'react';
import './App.css';
import {
  RotateCcw,
  Database,
  FileCode,
  BookOpen,
  Send,
  Copy,
  Check,
  Terminal,
  Activity,
  AlertCircle,
  Clock,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Edit3,
  Play
} from 'lucide-react';
import ArchitectureSection from './components/ArchitectureSection';

const PRESETS = [
  {
    type: 'sql',
    label: 'Top 2 Highest-Paid Employees',
    tag: 'SQL Analyst',
    icon: Database,
    prompt: "Retrieve the names and salaries of the top 2 highest-paid employees in our database"
  },
  {
    type: 'sql',
    label: '⚠️ Destructive Query (Triggers HITL)',
    tag: 'HITL Security Check',
    icon: ShieldAlert,
    prompt: "Delete all records from the employee table where salary > 30000"
  },
  {
    type: 'etl',
    label: 'PokeAPI Extraction to CSV',
    tag: 'Autonomous ETL',
    icon: FileCode,
    prompt: "I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder"
  },
  {
    type: 'rag',
    label: 'Company Privacy Policy',
    tag: 'Corporate RAG',
    icon: BookOpen,
    prompt: "Explain the company's privacy policy regarding customer personal information and data protection."
  }
];

export default function App() {
  const [query, setQuery] = useState(PRESETS[0].prompt);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [isSpinning, setIsSpinning] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [copied, setCopied] = useState(false);
  const [sqlCopied, setSqlCopied] = useState(false);
  const [viewRaw, setViewRaw] = useState(false);

  // Human-in-the-Loop (HITL) State
  const [requireHitl, setRequireHitl] = useState(false);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [editableSql, setEditableSql] = useState('');
  const [isEditingSql, setIsEditingSql] = useState(false);

  // Check backend server status on mount
  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        setIsBackendOnline(true);
      } else {
        setIsBackendOnline(false);
      }
    } catch {
      setIsBackendOnline(false);
    }
  };

  // Triggered when user clicks "Refresh UI"
  const handleRefresh = async () => {
    setIsSpinning(true);
    setToastMessage('Refreshing interface & clearing state...');

    // Reset query & output
    setQuery('');
    setResponse(null);
    setViewRaw(false);
    setCopied(false);
    setSqlCopied(false);
    setEditableSql('');
    setIsEditingSql(false);

    // Re-verify backend
    await checkHealth();

    setTimeout(() => {
      setIsSpinning(false);
      setToastMessage('UI Refreshed: Ready for new query');
      setTimeout(() => setToastMessage(null), 3500);
    }, 600);
  };

  // Submit Query to DataAgent
  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setResponse(null);
    setViewRaw(false);
    setIsEditingSql(false);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: query,
          require_approval: requireHitl
        })
      });

      let data;
      try {
        data = await res.json();
      } catch {
        if (!res.ok) {
          throw new Error(`Backend service unreachable (HTTP ${res.status} Bad Gateway). Please ensure the Python server (python server.py) is running on port 8000.`);
        }
        throw new Error('Unexpected empty or invalid response from backend server.');
      }

      if (!res.ok || !data.success) {
        throw new Error(data.error || `Server responded with status ${res.status}`);
      }

      setResponse(data);
      if (data.needs_approval && data.approval_data) {
        setEditableSql(data.approval_data.sql_query || '');
        setToastMessage(' Action Paused: Human-in-the-Loop authorization required.');
        setTimeout(() => setToastMessage(null), 5000);
      }
      setIsBackendOnline(true);
    } catch (err) {
      console.error(err);
      setResponse({
        success: false,
        error: err.message || 'Failed to connect to DataAgent backend. Ensure python server.py is running on port 8000.'
      });
      checkHealth();
    } finally {
      setLoading(false);
    }
  };

  // Operator Approves SQL Execution
  const handleApprove = async () => {
    if (!response || !response.approval_data) return;
    setApprovalLoading(true);
    setToastMessage('Authorization Granted: Executing query on PostgreSQL database...');

    try {
      const res = await fetch('/api/approve-sql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision: 'approved',
          sql_query: editableSql || response.approval_data.sql_query,
          user_question: response.approval_data.user_question,
          curated_ques: response.approval_data.curated_ques
        })
      });

      let data;
      try {
        data = await res.json();
      } catch {
        throw new Error(`Server returned HTTP ${res.status}. Could not parse response.`);
      }

      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Failed to execute approved SQL query');
      }

      setResponse(data);
      setToastMessage(' Query executed and answer synthesized!');
      setTimeout(() => setToastMessage(null), 4000);
    } catch (err) {
      console.error(err);
      setToastMessage(`Error: ${err.message}`);
    } finally {
      setApprovalLoading(false);
    }
  };

  // Operator Denies SQL Execution
  const handleDeny = async () => {
    if (!response || !response.approval_data) return;
    setApprovalLoading(true);
    setToastMessage('Authorization Denied: Canceling execution...');

    try {
      const res = await fetch('/api/approve-sql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision: 'denied',
          sql_query: response.approval_data.sql_query,
          user_question: response.approval_data.user_question
        })
      });

      let data;
      try {
        data = await res.json();
      } catch {
        data = { success: true, result: 'Execution canceled by operator.' };
      }

      setResponse(data);
      setToastMessage(' Execution canceled by human operator.');
      setTimeout(() => setToastMessage(null), 4000);
    } catch (err) {
      console.error(err);
      setToastMessage(`Error: ${err.message}`);
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit();
    }
  };

  const handleCopy = () => {
    if (!response) return;
    const textToCopy = typeof response.result === 'object' ? JSON.stringify(response.result, null, 2) : response.result;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopySql = () => {
    if (!editableSql && (!response || !response.approval_data)) return;
    const text = editableSql || response.approval_data.sql_query;
    navigator.clipboard.writeText(text);
    setSqlCopied(true);
    setTimeout(() => setSqlCopied(false), 2000);
  };

  return (
    <div className="app-container">
      {/* -------------------- TOP NAVIGATION BAR -------------------- */}
      <header className="navbar">
        <div className="nav-brand">
          <div className="brand-logo-container">
            <img src="/image.png" alt="DataAgent Logo" className="brand-logo-image" />
          </div>
          <div className="brand-details">
            <span className="brand-title">DataAgent</span>
            <div className="brand-subtitle">
              <span>Autonomous Multi-Agent Platform</span>
            </div>
          </div>
        </div>

        <div className="nav-actions">
          <button
            id="refresh-ui-button"
            className={`refresh-button ${isSpinning ? 'spinning' : ''}`}
            onClick={handleRefresh}
            title="Refresh UI, clear state & re-check connection"
          >
            <RotateCcw size={16} className="refresh-icon" />
            <span>Refresh UI</span>
          </button>
        </div>
      </header>

      {/* -------------------- MAIN CONTENT CONTAINER -------------------- */}
      <main className="main-content">
        {/* Toast Alert */}
        {toastMessage && (
          <div className="toast-bar animate-fade-in">
            <span>{toastMessage}</span>
          </div>
        )}

        {/* System Architecture Section */}
        <ArchitectureSection />

        {/* Preset Queries Section */}
        <section className="presets-container">
          <div className="presets-label">
            <Sparkles size={14} /> Quick Presets & Scenarios
          </div>
          <div className="presets-grid">
            {PRESETS.map((p, idx) => {
              const Icon = p.icon;
              return (
                <button
                  key={idx}
                  className="preset-chip"
                  onClick={() => setQuery(p.prompt)}
                >
                  <span className={`preset-chip-tag ${p.type}`}>
                    <Icon size={12} /> {p.tag}
                  </span>
                  <span className="preset-chip-text">{p.prompt}</span>
                </button>
              );
            })}
          </div>
        </section>

        {/* -------------------- QUERY INPUT CARD -------------------- */}
        <section className="card">
          <div className="card-header">
            <div className="card-title">
              <Terminal size={20} style={{ color: 'var(--color-primary-light)' }} />
              <span>Input Query</span>
            </div>
            <div className="card-subtitle">
              Natural language prompt for SQL Analytics (with HITL), ETL Pipelines, or Corporate RAG
            </div>
          </div>

          <div className="input-wrapper">
            <textarea
              id="query-input"
              className="query-textarea"
              placeholder="Enter your instruction (e.g. 'Retrieve top 2 highest-paid employees', 'Delete all records from employee', or 'Explain privacy policy')..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />

            <div className="input-footer">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
                <div className="input-shortcuts">
                  <span>Shortcut:</span>
                  <span className="kbd">Ctrl</span> + <span className="kbd">Enter</span>
                </div>

                <label className="hitl-checkbox-container" title="Always pause and ask human operator before executing any SQL query">
                  <input
                    type="checkbox"
                    className="hitl-checkbox"
                    checked={requireHitl}
                    onChange={(e) => setRequireHitl(e.target.checked)}
                    disabled={loading}
                  />
                  <ShieldCheck size={14} style={{ color: requireHitl ? '#6366f1' : '#94a3b8' }} />
                  <span>Force Human Review for SQL</span>
                </label>
              </div>

              <div className="input-button-group">
                {query && (
                  <button
                    type="button"
                    className="clear-btn"
                    onClick={() => setQuery('')}
                    disabled={loading}
                  >
                    Clear
                  </button>
                )}
                <button
                  id="submit-query-btn"
                  className="submit-btn"
                  onClick={handleSubmit}
                  disabled={loading || !query.trim()}
                >
                  {loading ? (
                    <>
                      <div className="loading-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                      <span>Processing Agent...</span>
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      <span>Run Requisition</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* -------------------- QUERY OUTPUT CARD -------------------- */}
        <section className="card output-card">
          <div className="output-header">
            <div className="output-meta">
              <div className="card-title">
                <Activity size={20} style={{ color: 'var(--color-cyan)' }} />
                <span>Agent Execution Output</span>
              </div>

              {response && response.success && (
                <>
                  <span className={`route-pill ${response.route || 'sql'}`}>
                    Routed Agent: {response.route ? response.route.toUpperCase() : 'DATA AGENT'}
                  </span>
                  {response.needs_approval && (
                    <span className="hitl-badge">
                      <ShieldAlert size={12} /> Awaiting Human Approval
                    </span>
                  )}
                  {response.elapsedSeconds && (
                    <span className="output-stat">
                      <Clock size={14} /> {response.elapsedSeconds}s
                    </span>
                  )}
                </>
              )}
            </div>

            {response && response.success && (
              <div className="output-actions">
                <button
                  className="icon-action-btn"
                  onClick={() => setViewRaw(!viewRaw)}
                >
                  <FileCode size={14} />
                  <span>{viewRaw ? 'Formatted' : 'Raw'}</span>
                </button>
                <button
                  className="icon-action-btn"
                  onClick={handleCopy}
                  title="Copy result to clipboard"
                >
                  {copied ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Loading View */}
          {loading && (
            <div className="loading-box animate-fade-in">
              <div className="loading-spinner" />
              <div className="loading-title">DataAgent is Analyzing & Routing...</div>
              <div className="loading-subtitle">
                Evaluating security constraints, introspecting schema, and preparing agent execution pipeline.
              </div>
            </div>
          )}

          {/* Error View */}
          {response && !response.success && (
            <div className="error-box animate-fade-in">
              <div className="error-title">
                <AlertCircle size={18} />
                <span>Execution Failed</span>
              </div>
              <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
                {response.error}
              </p>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Tip: Run <code>uv run python server.py</code> in your project terminal to start the DataAgent API backend.
              </div>
            </div>
          )}

          {/* -------------------- HUMAN-IN-THE-LOOP INTERACTIVE REVIEW CARD -------------------- */}
          {response && response.success && response.needs_approval && response.approval_data && (
            <div className="hitl-banner animate-fade-in">
              <div className="hitl-header">
                <div className="hitl-title-group">
                  <ShieldAlert size={24} color="#fbbf24" />
                  <span className="hitl-title">Human-in-the-Loop Authorization Required</span>
                </div>
                <div className="hitl-badge">
                  {response.approval_data.judge_status === 'Yes' ? 'Manual Inspection Policy' : 'Security Flagged: Destructive SQL'}
                </div>
              </div>

              <div className="hitl-grid">
                <div className="hitl-card-item">
                  <div className="hitl-item-label">Original User Query</div>
                  <div className="hitl-item-value">{response.approval_data.user_question}</div>
                </div>
                <div className="hitl-card-item">
                  <div className="hitl-item-label">Security Judge Verdict</div>
                  <div className="hitl-item-value" style={{ color: response.approval_data.judge_status === 'Yes' ? '#34d399' : '#f87171', fontWeight: 700 }}>
                    {response.approval_data.judge_status === 'Yes' ? 'Safe Query (Operator Review Enforced)' : 'Potentially Unsafe (Modification/Deletion detected)'}
                  </div>
                </div>
                <div className="hitl-card-item" style={{ gridColumn: '1 / -1' }}>
                  <div className="hitl-item-label">Security Judge Remarks & Rationale</div>
                  <div className="hitl-item-value" style={{ fontStyle: 'italic', color: '#cbd5e1' }}>
                    {response.approval_data.judge_comments || 'Review query structure before execution.'}
                  </div>
                </div>
              </div>

              {/* Generated SQL Box */}
              <div className="hitl-sql-box">
                <div className="hitl-sql-header">
                  <span>Generated SQL Statement (Target: PostgreSQL public schema)</span>
                  <div className="hitl-sql-header-actions">
                    <button
                      type="button"
                      className="hitl-mini-btn"
                      onClick={() => setIsEditingSql(!isEditingSql)}
                    >
                      <Edit3 size={12} />
                      <span>{isEditingSql ? 'Done Editing' : 'Edit Query'}</span>
                    </button>
                    <button
                      type="button"
                      className="hitl-mini-btn"
                      onClick={handleCopySql}
                    >
                      {sqlCopied ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
                      <span>{sqlCopied ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                </div>

                {isEditingSql ? (
                  <textarea
                    className="hitl-sql-textarea"
                    value={editableSql}
                    onChange={(e) => setEditableSql(e.target.value)}
                    placeholder="Enter or adjust SQL query..."
                  />
                ) : (
                  <pre className="hitl-sql-code">{editableSql || response.approval_data.sql_query}</pre>
                )}
              </div>

              {/* Action Buttons */}
              <div className="hitl-actions">
                <button
                  type="button"
                  className="hitl-btn hitl-deny-btn"
                  onClick={handleDeny}
                  disabled={approvalLoading}
                >
                  <XCircle size={16} />
                  <span>Reject & Abort Execution</span>
                </button>

                <button
                  type="button"
                  className="hitl-btn hitl-approve-btn"
                  onClick={handleApprove}
                  disabled={approvalLoading}
                >
                  {approvalLoading ? (
                    <>
                      <div className="loading-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                      <span>Executing on DB...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={16} />
                      <span>Approve & Execute Query</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Standard Result Output View */}
          {response && response.success && (
            <div className="output-body animate-fade-in">
              {viewRaw ? (
                <pre>{JSON.stringify(response, null, 2)}</pre>
              ) : (
                <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {response.result}
                </div>
              )}
            </div>
          )}

          {/* Empty Idle State */}
          {!loading && !response && (
            <div className="empty-state">
              <div className="empty-icon">
                <Sparkles size={28} />
              </div>
              <div>
                <h3 className="empty-title">Ready for Requisitions</h3>
                <p className="empty-desc">
                  Run SQL analytics with interactive Human-in-the-Loop verification, autonomous ETL pipelines, or hybrid corporate RAG search.
                </p>
              </div>

              <div className="agent-cards-preview">
                <div className="agent-preview-card">
                  <h4 style={{ color: 'var(--color-emerald)' }}>
                    <Database size={16} /> SQL Analyst + HITL
                  </h4>
                  <p>Introspects PostgreSQL schema, validates safety with AI judge, and presents interactive human approval before executing destructive queries.</p>
                </div>

                <div className="agent-preview-card">
                  <h4 style={{ color: 'var(--color-cyan)' }}>
                    <FileCode size={16} /> Autonomous ETL
                  </h4>
                  <p>Fetches REST endpoints, transforms datasets via Pandas, and outputs structured CSV files.</p>
                </div>

                <div className="agent-preview-card">
                  <h4 style={{ color: 'var(--color-primary-light)' }}>
                    <BookOpen size={16} /> Corporate RAG
                  </h4>
                  <p>Performs hybrid dense/sparse retrieval with Cross-Encoder reranking and grounded citations over company documents.</p>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
