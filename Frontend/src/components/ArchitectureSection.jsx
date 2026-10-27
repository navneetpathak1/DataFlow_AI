import React, { useState } from 'react';
import './ArchitectureSection.css';
import {
  Workflow,
  Layers,
  Database,
  FileCode,
  BookOpen,
  ShieldAlert,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Cpu,
  ArrowRight,
  ArrowDown,
  Server,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  GitFork,
  Sparkles,
  Lock,
  RefreshCw
} from 'lucide-react';

export default function ArchitectureSection() {
  const [isExpanded, setIsExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState('pipeline'); // 'pipeline' | 'agents' | 'hitl'

  return (
    <section className="arch-section" aria-label="System Architecture">
      {/* ----------------- ARCHITECTURE HEADER ----------------- */}
      <div 
        className="arch-header" 
        onClick={() => setIsExpanded(!isExpanded)}
        title="Click to toggle system architecture view"
      >
        <div className="arch-header-left">
          <div className="arch-icon-badge">
            <Workflow size={22} />
          </div>
          <div className="arch-title-group">
            <div className="arch-title">
              <span>System Architecture & Autonomous Pipeline</span>
            </div>
            <span className="arch-subtitle">
              Enterprise Multi-Agent Orchestration • Human-in-the-Loop Guardrail • LangGraph & React 19
            </span>
          </div>
          <div className="arch-badges">
            <span className="arch-badge arch-badge-blue">
              <Cpu size={12} /> LangGraph Multi-Agent
            </span>
            <span className="arch-badge arch-badge-purple">
              <ShieldCheck size={12} /> HITL Safety Guardrail
            </span>
            <span className="arch-badge arch-badge-amber">
              <Sparkles size={12} /> Hybrid RAG & ETL
            </span>
          </div>
        </div>

        <div className="arch-header-right">
          <button 
            type="button" 
            className="arch-toggle-btn" 
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
          >
            {isExpanded ? (
              <>
                <ChevronUp size={15} />
                <span>Hide Architecture</span>
              </>
            ) : (
              <>
                <ChevronDown size={15} />
                <span>View Architecture</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ----------------- EXPANDED CONTENT ----------------- */}
      {isExpanded && (
        <div className="arch-content">
          {/* Navigation Tabs */}
          <div className="arch-nav-tabs">
            <button
              type="button"
              className={`arch-tab-btn ${activeTab === 'pipeline' ? 'active' : ''}`}
              onClick={() => setActiveTab('pipeline')}
            >
              <Workflow size={15} />
              <span>Interactive Pipeline Flow</span>
            </button>
            <button
              type="button"
              className={`arch-tab-btn ${activeTab === 'agents' ? 'active' : ''}`}
              onClick={() => setActiveTab('agents')}
            >
              <Layers size={15} />
              <span>Specialized Agents Deep Dive</span>
            </button>
            <button
              type="button"
              className={`arch-tab-btn ${activeTab === 'hitl' ? 'active' : ''}`}
              onClick={() => setActiveTab('hitl')}
            >
              <ShieldAlert size={15} />
              <span>Safety Judge & HITL Protocol</span>
            </button>
          </div>

          {/* TAB 1: INTERACTIVE PIPELINE FLOW */}
          {activeTab === 'pipeline' && (
            <div className="pipeline-flow-wrapper">
              {/* STAGE 1: INGESTION & GATEWAY */}
              <div className="flow-stage">
                <div className="flow-stage-title">
                  <Terminal size={14} /> Stage 1: Ingestion & Gateway Layer
                  <span className="tag">HTTP & CORS</span>
                </div>
                <div className="gateway-grid">
                  <div className="flow-node-card">
                    <div className="flow-node-header">
                      <div className="flow-node-title">
                        <Terminal size={16} style={{ color: '#0284c7' }} />
                        <span>Client Prompt</span>
                      </div>
                      <span className="flow-node-tag tag-client">Frontend</span>
                    </div>
                    <p className="flow-node-desc">
                      Natural language question inputted via React 19 UI with optional "Force Human Review" flag.
                    </p>
                    <div className="flow-node-meta">
                      <span>Payload: JSON</span>
                      <span>App.jsx</span>
                    </div>
                  </div>

                  <div className="flow-node-card">
                    <div className="flow-node-header">
                      <div className="flow-node-title">
                        <Server size={16} style={{ color: '#475569' }} />
                        <span>API Server</span>
                      </div>
                      <span className="flow-node-tag tag-api">Backend</span>
                    </div>
                    <p className="flow-node-desc">
                      Multi-threaded HTTP daemon handling <code>/api/query</code> and <code>/api/approve-sql</code> endpoints.
                    </p>
                    <div className="flow-node-meta">
                      <span>Port 8000</span>
                      <span>server.py</span>
                    </div>
                  </div>

                  <div className="flow-node-card highlight">
                    <div className="flow-node-header">
                      <div className="flow-node-title">
                        <GitFork size={16} style={{ color: '#7C3AED' }} />
                        <span>Supervisor Router</span>
                      </div>
                      <span className="flow-node-tag tag-router">LangGraph</span>
                    </div>
                    <p className="flow-node-desc">
                      Evaluates intent using Pydantic <code>RouterSchema</code> and classifies destination to SQL, ETL, or RAG.
                    </p>
                    <div className="flow-node-meta">
                      <span>Pydantic v2</span>
                      <span>data_agent.py</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Connecting Divider */}
              <div className="flow-connector-horizontal">
                <span className="flow-connector-pill">
                  <ArrowDown size={14} /> Dynamic Intent Dispatch to Specialized Agent Tracks <ArrowDown size={14} />
                </span>
              </div>

              {/* STAGE 2: 3 PARALLEL SPECIALIZED AGENT TRACKS */}
              <div className="agents-tracks-grid">
                {/* TRACK 1: SQL ANALYST */}
                <div className="agent-track-column">
                  <div className="track-header sql">
                    <div className="track-title-wrap">
                      <Database size={18} style={{ color: '#1E40AF' }} />
                      <span className="track-title">SQL Analyst Agent</span>
                    </div>
                    <span className="track-badge">Postgres + HITL</span>
                  </div>
                  <div className="track-body">
                    <div className="track-step-item">
                      <span className="step-num">1</span>
                      <div className="step-content">
                        <span className="step-title">Curate Question</span>
                        <span className="step-detail">Clarifies intent & removes ambiguity</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">2</span>
                      <div className="step-content">
                        <span className="step-title">Schema Introspection</span>
                        <span className="step-detail">Extracts live tables, columns & sample rows</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">3</span>
                      <div className="step-content">
                        <span className="step-title">SQL Generation</span>
                        <span className="step-detail">Generates PostgreSQL query with default LIMIT 5</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">4</span>
                      <div className="step-content">
                        <span className="step-title">AI Safety Judge</span>
                        <span className="step-detail">Evaluates query for DROP, DELETE, UPDATE</span>
                      </div>
                    </div>

                    <div className="track-hitl-callout">
                      <ShieldAlert size={18} style={{ color: '#E11D48', flexShrink: 0 }} />
                      <div className="hitl-text">
                        <strong>HITL Intercept:</strong> If destructive query or approval requested, execution halts for operator review in UI.
                      </div>
                    </div>

                    <div className="track-step-item">
                      <span className="step-num">5</span>
                      <div className="step-content">
                        <span className="step-title">Database Execution</span>
                        <span className="step-detail">Runs on PostgreSQL & synthesizes answer</span>
                      </div>
                    </div>
                  </div>
                  <div className="track-footer">
                    <span>Target: Relational DB</span>
                    <div className="track-tech-stack">
                      <span className="tech-pill">psycopg2</span>
                      <span className="tech-pill">LangGraph</span>
                    </div>
                  </div>
                </div>

                {/* TRACK 2: AUTONOMOUS ETL */}
                <div className="agent-track-column">
                  <div className="track-header etl">
                    <div className="track-title-wrap">
                      <FileCode size={18} style={{ color: '#B45309' }} />
                      <span className="track-title">Autonomous ETL Agent</span>
                    </div>
                    <span className="track-badge">API & Pandas</span>
                  </div>
                  <div className="track-body">
                    <div className="track-step-item">
                      <span className="step-num">1</span>
                      <div className="step-content">
                        <span className="step-title">Tool Decision Node</span>
                        <span className="step-detail">Selects extraction vs transformation</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">2</span>
                      <div className="step-content">
                        <span className="step-title">Extract & Load Tool</span>
                        <span className="step-detail">Fetches REST API endpoints & scrapes HTML</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">3</span>
                      <div className="step-content">
                        <span className="step-title">Pandas Code Synthesis</span>
                        <span className="step-detail">Generates on-the-fly Python Pandas script</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">4</span>
                      <div className="step-content">
                        <span className="step-title">Isolated Execution</span>
                        <span className="step-detail">Runs transformation with DataFrame validation</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">5</span>
                      <div className="step-content">
                        <span className="step-title">Data Export</span>
                        <span className="step-detail">Saves to data/extract/*.csv, JSON, or Parquet</span>
                      </div>
                    </div>
                  </div>
                  <div className="track-footer">
                    <span>Target: REST APIs & Files</span>
                    <div className="track-tech-stack">
                      <span className="tech-pill">Pandas</span>
                      <span className="tech-pill">BeautifulSoup</span>
                    </div>
                  </div>
                </div>

                {/* TRACK 3: CORPORATE RAG */}
                <div className="agent-track-column">
                  <div className="track-header rag">
                    <div className="track-title-wrap">
                      <BookOpen size={18} style={{ color: '#047857' }} />
                      <span className="track-title">Corporate RAG Agent</span>
                    </div>
                    <span className="track-badge">FAISS + BM25</span>
                  </div>
                  <div className="track-body">
                    <div className="track-step-item">
                      <span className="step-num">1</span>
                      <div className="step-content">
                        <span className="step-title">Document Loading</span>
                        <span className="step-detail">Ingests 11+ corporate PDFs (Earnings, Policies)</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">2</span>
                      <div className="step-content">
                        <span className="step-title">Dense Embeddings</span>
                        <span className="step-detail">sentence-transformers/all-MiniLM-L6-v2</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">3</span>
                      <div className="step-content">
                        <span className="step-title">Sparse Keyword Search</span>
                        <span className="step-detail">BM25 exact token matching</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">4</span>
                      <div className="step-content">
                        <span className="step-title">Hybrid Ensemble (RRF)</span>
                        <span className="step-detail">Fuses dense FAISS + sparse BM25 scores</span>
                      </div>
                    </div>
                    <div className="track-step-item">
                      <span className="step-num">5</span>
                      <div className="step-content">
                        <span className="step-title">Cross-Encoder Reranker</span>
                        <span className="step-detail">Reranks candidates to ensure strict ground truth</span>
                      </div>
                    </div>
                  </div>
                  <div className="track-footer">
                    <span>Target: Enterprise PDFs</span>
                    <div className="track-tech-stack">
                      <span className="tech-pill">FAISS</span>
                      <span className="tech-pill">CrossEncoder</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* STAGE 3: SYNTHESIS & OUTPUT */}
              <div className="flow-stage" style={{ background: '#FFFFFF' }}>
                <div className="flow-stage-title">
                  <CheckCircle2 size={14} style={{ color: '#059669' }} /> Stage 3: Synthesis & Operator Dashboard
                  <span className="tag">Unified Delivery</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
                  <div style={{ fontSize: '0.82rem', color: '#475569', maxWidth: '800px', lineHeight: 1.5 }}>
                    The target agent returns final synthesized output to the supervisor. The API server bundles elapsed duration metrics, route classification, and any pending HITL authorization states before rendering on the <strong>React 19 Dashboard</strong>.
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <span className="tech-pill" style={{ background: '#EFF6FF', color: '#1D4ED8' }}>Formatted Markdown</span>
                    <span className="tech-pill" style={{ background: '#F8FAFC', color: '#334155' }}>Raw JSON Inspection</span>
                    <span className="tech-pill" style={{ background: '#ECFDF5', color: '#047857' }}>Latency Metrics</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: SPECIALIZED AGENTS DEEP DIVE */}
          {activeTab === 'agents' && (
            <div className="deep-dive-grid">
              {/* Supervisor Router */}
              <div className="deep-card">
                <div className="deep-card-top">
                  <div className="deep-card-icon icon-supervisor">
                    <GitFork size={20} />
                  </div>
                  <div className="deep-card-meta">
                    <span className="deep-card-name">Supervisor Router</span>
                    <span className="deep-card-file">agents/data_agent.py</span>
                  </div>
                </div>
                <p className="deep-card-desc">
                  Central coordinator orchestrating state transitions using LangGraph channels. It uses Pydantic structured output classification to guarantee schema-safe routing.
                </p>
                <ul className="deep-card-points">
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Structured output via <code>RouterSchema</code> with regex fallback.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span>State Reducer updates without message duplication.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Propagates HITL flags and approval decisions seamlessly.</span>
                  </li>
                </ul>
                <div className="deep-card-tags">
                  <span className="tech-pill">LangGraph 1.2+</span>
                  <span className="tech-pill">Pydantic v2</span>
                  <span className="tech-pill">Groq LPU</span>
                </div>
              </div>

              {/* SQL Analyst */}
              <div className="deep-card">
                <div className="deep-card-top">
                  <div className="deep-card-icon icon-sql">
                    <Database size={20} />
                  </div>
                  <div className="deep-card-meta">
                    <span className="deep-card-name">Text-to-SQL Analyst</span>
                    <span className="deep-card-file">agents/sql_analyst.py</span>
                  </div>
                </div>
                <p className="deep-card-desc">
                  Transforms natural language into executable PostgreSQL queries using real-time database schema reflection, query limits, and AI safety inspection.
                </p>
                <ul className="deep-card-points">
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Live <code>information_schema</code> table & column introspection.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Default <code>LIMIT 5</code> rule prevents unconstrained server memory load.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Safety Judge intercepts mutations (<code>DROP</code>, <code>DELETE</code>, <code>UPDATE</code>).</span>
                  </li>
                </ul>
                <div className="deep-card-tags">
                  <span className="tech-pill">PostgreSQL</span>
                  <span className="tech-pill">psycopg2</span>
                  <span className="tech-pill">HITL Intercept</span>
                </div>
              </div>

              {/* Autonomous ETL */}
              <div className="deep-card">
                <div className="deep-card-top">
                  <div className="deep-card-icon icon-etl">
                    <FileCode size={20} />
                  </div>
                  <div className="deep-card-meta">
                    <span className="deep-card-name">Autonomous ETL Agent</span>
                    <span className="deep-card-file">agents/etl_analyst.py</span>
                  </div>
                </div>
                <p className="deep-card-desc">
                  Autonomous data engineering agent equipped with tools to fetch web APIs, scrape structured HTML, and dynamically write and execute Pandas data transformations.
                </p>
                <ul className="deep-card-points">
                  <li>
                    <CheckCircle2 size={14} />
                    <span><code>extract_load_tool</code>: REST JSON normalization & web scraping.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span><code>transform_load_tool</code>: Dynamic Pandas code synthesis & execution.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Persists clean tabular data to <code>data/extract/</code>.</span>
                  </li>
                </ul>
                <div className="deep-card-tags">
                  <span className="tech-pill">Pandas 3.0</span>
                  <span className="tech-pill">BeautifulSoup4</span>
                  <span className="tech-pill">CSV / Parquet</span>
                </div>
              </div>

              {/* Corporate RAG */}
              <div className="deep-card">
                <div className="deep-card-top">
                  <div className="deep-card-icon icon-rag">
                    <BookOpen size={20} />
                  </div>
                  <div className="deep-card-meta">
                    <span className="deep-card-name">Corporate RAG Agent</span>
                    <span className="deep-card-file">agents/rag.py</span>
                  </div>
                </div>
                <p className="deep-card-desc">
                  Enterprise document retrieval agent indexing 11+ corporate PDFs (Walmart SEC filings, Q2 earnings presentations, Code of Conduct) with hybrid search and reranking.
                </p>
                <ul className="deep-card-points">
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Dense vector retrieval with FAISS and <code>all-MiniLM-L6-v2</code>.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Sparse BM25 retriever for high precision keyword recall.</span>
                  </li>
                  <li>
                    <CheckCircle2 size={14} />
                    <span>Cross-Encoder reranking ensures grounded, hallucination-free answers.</span>
                  </li>
                </ul>
                <div className="deep-card-tags">
                  <span className="tech-pill">FAISS CPU</span>
                  <span className="tech-pill">BM25</span>
                  <span className="tech-pill">CrossEncoder</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SAFETY JUDGE & HITL PROTOCOL */}
          {activeTab === 'hitl' && (
            <div className="hitl-explanation-panel">
              <div className="hitl-banner-overview">
                <ShieldAlert size={28} style={{ color: '#E11D48', flexShrink: 0 }} />
                <div className="hitl-overview-text">
                  <h4>Human-in-the-Loop (HITL) Execution Guardrail</h4>
                  <p>
                    DataAgent strictly isolates database mutation privileges. Any query containing commands that can alter database schemas or row contents (<code>INSERT</code>, <code>UPDATE</code>, <code>DELETE</code>, <code>DROP</code>, <code>ALTER</code>, <code>TRUNCATE</code>) or requests flagged with "Force Human Review" will trigger an immediate execution pause.
                  </p>
                </div>
              </div>

              <div className="hitl-steps-grid">
                <div className="hitl-step-card">
                  <span className="hitl-step-badge hitl-badge-red">Step 1: Automated Detection</span>
                  <span className="hitl-step-title">AI Safety Judge Node</span>
                  <p className="hitl-step-detail">
                    Every generated SQL query is passed into <code>is_safe_sql()</code>, which leverages structured JSON evaluation via <code>JudgeSchema</code> to test for data mutations and SQL injections.
                  </p>
                </div>

                <div className="hitl-step-card">
                  <span className="hitl-step-badge hitl-badge-blue">Step 2: Execution Intercept</span>
                  <span className="hitl-step-title">Non-Destructive Pause</span>
                  <p className="hitl-step-detail">
                    Instead of routing to <code>execute_sql</code>, the graph redirects to <code>human_approval</code> and enters the <code>awaiting_approval</code> state. No SQL touches the PostgreSQL database.
                  </p>
                </div>

                <div className="hitl-step-card">
                  <span className="hitl-step-badge hitl-badge-green">Step 3: Operator Action</span>
                  <span className="hitl-step-title">Review, Edit, or Deny</span>
                  <p className="hitl-step-detail">
                    The web dashboard reveals the intercepted SQL query, risk assessment, and interactive controls. The operator can modify the SQL directly and click <strong>Approve</strong> or <strong>Deny Execution</strong>.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
