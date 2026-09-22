import React, { useState, useEffect } from 'react';
import './App.css';
import {
  RotateCcw,
  Bot,
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
  ArrowRight
} from 'lucide-react';

const PRESETS = [
  {
    type: 'etl',
    label: 'PokeAPI ETL (main.py requisition)',
    tag: 'Autonomous ETL',
    icon: FileCode,
    prompt: "I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder"
  },
  {
    type: 'sql',
    label: 'Payment Methods Analysis',
    tag: 'SQL Analyst',
    icon: Database,
    prompt: "What are the different types of Payment Methods we have in our database?"
  },
  {
    type: 'etl',
    label: 'Filter & Transform Bulbasaur',
    tag: 'Autonomous ETL',
    icon: FileCode,
    prompt: "I want to transform the data stored in the 'data/extract/extracted_data.csv' file and save the transformed data in the 'data/transform' folder in csv format. Filter for bulbasaur only."
  },
  {
    type: 'rag',
    label: 'Cancer Treatment Options',
    tag: 'Medical RAG',
    icon: BookOpen,
    prompt: "Using the medical notes, explain the treatment options for cancer"
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
  const [viewRaw, setViewRaw] = useState(false);

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
    } catch (e) {
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

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query })
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || `Server responded with status ${res.status}`);
      }

      setResponse(data);
      setIsBackendOnline(true);
    } catch (err) {
      console.error(err);
      setResponse({
        success: false,
        error: err.message || 'Failed to connect to DataAgent backend. Ensure python server.py is running.'
      });
      checkHealth();
    } finally {
      setLoading(false);
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

  return (
    <div className="app-container">
      {/* -------------------- TOP NAVIGATION BAR -------------------- */}
      <header className="navbar">
        <div className="nav-brand">
          <div className="brand-icon-wrapper">
            <Bot size={26} />
          </div>
          <div className="brand-details">
            <span className="brand-title">DataAgent</span>
            <div className="brand-subtitle">
              <span>Autonomous Multi-Agent Platform</span>
              <span className={`status-badge ${isBackendOnline === false ? 'offline' : ''}`}>
                <span className="status-dot" />
                {isBackendOnline === true ? 'Backend Online' : isBackendOnline === false ? 'Backend Offline' : 'Checking...'}
              </span>
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
            <RotateCcw size={16} />
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

        {/* Preset Queries Section */}
        <section className="presets-container">
          <div className="presets-label">
            <Sparkles size={14} /> Quick Presets (Includes main.py query)
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
              Natural language prompt for SQL Analytics, ETL Pipelines, or Medical RAG
            </div>
          </div>

          <div className="input-wrapper">
            <textarea
              id="query-input"
              className="query-textarea"
              placeholder="Enter your instruction (e.g. 'Extract data from API and save to CSV', 'How many total rides occurred in 2024?', or 'Explain symptoms of diabetes')..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />

            <div className="input-footer">
              <div className="input-shortcuts">
                <span>Shortcut:</span>
                <span className="kbd">Ctrl</span> + <span className="kbd">Enter</span> to execute
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
                  <span className={`route-pill ${response.route || 'etl'}`}>
                    Routed Agent: {response.route ? response.route.toUpperCase() : 'DATA AGENT'}
                  </span>
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
              <div className="loading-title">DataAgent is Analyzing & Executing...</div>
              <div className="loading-subtitle">
                Router classifying request into SQL, ETL, or RAG node and invoking agent pipeline.
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

          {/* Result Output View */}
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
                <Bot size={28} />
              </div>
              <div>
                <h3 className="empty-title">Ready for Requisitions</h3>
                <p className="empty-desc">
                  Submit an API extraction task, run database analytics on PostgreSQL, or search the medical knowledge base.
                </p>
              </div>

              <div className="agent-cards-preview">
                <div className="agent-preview-card">
                  <h4 style={{ color: 'var(--color-cyan)' }}>
                    <FileCode size={16} /> Autonomous ETL
                  </h4>
                  <p>Fetches REST APIs (e.g. PokeAPI), normalizes JSON, generates Pandas code, and outputs CSV/Parquet.</p>
                </div>

                <div className="agent-preview-card">
                  <h4 style={{ color: 'var(--color-emerald)' }}>
                    <Database size={16} /> SQL Analyst
                  </h4>
                  <p>Introspects DB schema and records, generates safe SQL queries, and explains answers in natural language.</p>
                </div>

                <div className="agent-preview-card">
                  <h4 style={{ color: 'var(--color-primary-light)' }}>
                    <BookOpen size={16} /> Medical RAG
                  </h4>
                  <p>Performs dense vector retrieval over medical encyclopedia documents using local FAISS embeddings.</p>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
