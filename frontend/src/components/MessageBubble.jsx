import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, User, Sparkles, AlertCircle, Database, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import SourceCard from './SourceCard';
import EscalationBanner from './EscalationBanner';

export default function MessageBubble({ message, onEscalateClick }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message-row user">
        <div className="message-body-wrap" style={{ alignItems: 'flex-end' }}>
          <div className="user-bubble">
            {message.content}
          </div>
        </div>
        <div className="avatar-badge user" title="You">
          <User size={18} />
        </div>
      </div>
    );
  }

  // Assistant Message
  const confidence = message.confidence != null ? Math.round(message.confidence * 100) : null;
  const sources = message.sources || [];
  const escalate = Boolean(message.escalate);
  const hasOutdated = Boolean(message.has_outdated_sources);

  let confidenceClass = 'confidence-medium';
  if (confidence != null) {
    if (confidence >= 80) confidenceClass = 'confidence-high';
    else if (confidence < 60) confidenceClass = 'confidence-low';
  }

  return (
    <div className="message-row assistant">
      <div className="avatar-badge assistant" title="LearnForge Assistant">
        <Bot size={18} />
      </div>

      <div className="message-body-wrap">
        <div className="assistant-bubble">
          <ReactMarkdown>{message.content || message.answer}</ReactMarkdown>
        </div>

        {/* Metadata Bar */}
        <div className="assistant-meta-bar">
          {confidence != null && (
            <span 
              className={`confidence-pill ${confidenceClass}`} 
              title={message.escalation_reason || `Confidence: ${confidence}% based on KB retrieval quality`}
            >
              <Sparkles size={12} />
              <span>{confidence}% Confidence</span>
            </span>
          )}

          {hasOutdated && (
            <span className="outdated-flag-pill" title="Superseded or older policy texts were analyzed and adjusted">
              <AlertTriangle size={12} />
              <span>Stale Data Filtered</span>
            </span>
          )}

          {sources.length > 0 && (
            <button 
              className="sources-toggle-btn"
              onClick={() => setShowSources(!showSources)}
              type="button"
            >
              <Database size={12} />
              <span>{sources.length} Sources</span>
              {showSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
        </div>

        {/* Escalation Alert */}
        {escalate && (
          <EscalationBanner 
            reason={message.escalation_reason} 
            onEscalateClick={onEscalateClick}
          />
        )}

        {/* Sources Accordion */}
        {showSources && sources.length > 0 && (
          <div className="sources-panel">
            <div className="sources-panel-title">
              Retrieved Knowledge Chunks (Qdrant Vector DB)
            </div>
            {sources.map((src, i) => (
              <SourceCard key={src.doc_id || i} chunk={src} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
