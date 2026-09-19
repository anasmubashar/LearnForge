import React from 'react';
import { 
  GraduationCap, 
  Layers, 
  Zap, 
  Cpu, 
  RefreshCw, 
  PlusCircle, 
  HelpCircle, 
  ShieldCheck, 
  ChevronRight,
  Database
} from 'lucide-react';

export default function Sidebar({ 
  onSelectSample, 
  onNewSession, 
  onReingest, 
  reingesting,
  isOpen,
  onClose
}) {
  const sampleQueries = [
    {
      label: 'Refund Policy & Stale Data',
      tag: 'Policy (14 vs 7-day)',
      query: 'What is the refund policy for courses?'
    },
    {
      label: 'Offline Video Access',
      tag: 'Mobile App FAQ',
      query: 'Can I download videos for offline viewing on mobile?'
    },
    {
      label: 'Tax Invoice Request',
      tag: 'Past Support Ticket',
      query: 'How do I request an invoice with my company VAT/Tax ID?'
    },
    {
      label: 'Out-of-Domain Escalation',
      tag: 'Human Escalation',
      query: 'How do I fix a flat tire on a bicycle?'
    },
    {
      label: 'Course Transfer Limits',
      tag: 'Policy Exception',
      query: 'Can I transfer my course to a coworker after 60 days?'
    }
  ];

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="brand-badge">
          <div className="brand-icon">
            <GraduationCap size={22} />
          </div>
          <div>
            <div className="brand-title">LearnForge</div>
            <div className="brand-subtitle">AI Support Agent</div>
          </div>
        </div>
      </div>

      {/* Sidebar Scrollable Body */}
      <div className="sidebar-content">
        {/* System Architecture Card */}
        <div>
          <div className="sidebar-section-title">Architecture & Models</div>
          
          <div className="metric-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={15} color="#8b5cf6" />
              <span className="metric-label">LLM Engine</span>
            </div>
            <span className="metric-val" style={{ fontSize: '0.8rem', color: '#a5b4fc' }}>
              Gemini 3.5 Flash Lite
            </span>
          </div>

          <div className="metric-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={15} color="#06b6d4" />
              <span className="metric-label">Vector Database</span>
            </div>
            <span className="metric-val" style={{ fontSize: '0.8rem', color: '#67e8f9' }}>
              Qdrant Cloud
            </span>
          </div>

          <div className="metric-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={15} color="#10b981" />
              <span className="metric-label">Indexed Chunks</span>
            </div>
            <span className="metric-val">40 Chunks</span>
          </div>

          <div className="metric-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={15} color="#f59e0b" />
              <span className="metric-label">Escalation Cutoff</span>
            </div>
            <span className="metric-val">&lt; 60% Match</span>
          </div>
        </div>

        {/* Quick Test Scenarios */}
        <div>
          <div className="sidebar-section-title">Quick Test Prompts</div>
          <div className="sample-queries-list">
            {sampleQueries.map((item, idx) => (
              <button
                key={idx}
                type="button"
                className="sample-query-btn"
                onClick={() => onSelectSample(item.query)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                  <span className="sample-query-tag">{item.tag}</span>
                  <ChevronRight size={12} color="#64748b" />
                </div>
                <span style={{ fontWeight: 500 }}>{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sidebar Footer Controls */}
      <div className="sidebar-footer">
        <button 
          className="btn-ghost" 
          style={{ width: '100%', justifyContent: 'center', padding: '9px 12px' }}
          onClick={onNewSession}
          type="button"
        >
          <PlusCircle size={15} />
          <span>Start New Session</span>
        </button>

        <button 
          className="btn-ghost" 
          style={{ width: '100%', justifyContent: 'center', padding: '9px 12px', fontSize: '0.78rem' }}
          onClick={onReingest}
          disabled={reingesting}
          type="button"
        >
          <RefreshCw size={14} className={reingesting ? 'animate-spin' : ''} />
          <span>{reingesting ? 'Re-indexing KB...' : 'Sync & Re-index KB'}</span>
        </button>
      </div>
    </aside>
  );
}
