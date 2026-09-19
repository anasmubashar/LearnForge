import React, { useState } from 'react';
import { BookOpen, FileText, LifeBuoy, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

export default function SourceCard({ chunk }) {
  const [expanded, setExpanded] = useState(false);

  const getIcon = (type) => {
    switch (type) {
      case 'policy':
        return <FileText size={13} className="text-purple-400" />;
      case 'ticket':
        return <LifeBuoy size={13} className="text-amber-400" />;
      default:
        return <BookOpen size={13} className="text-indigo-400" />;
    }
  };

  const scorePercent = Math.round(chunk.relevance_score * 100);

  return (
    <div className="source-item-card">
      <div 
        className="source-card-top" 
        onClick={() => setExpanded(!expanded)} 
        style={{ cursor: 'pointer', userSelect: 'none' }}
      >
        <div className="source-tag-group">
          <span className="source-id-badge">
            {getIcon(chunk.doc_type)}
            <span style={{ marginLeft: '4px' }}>{chunk.doc_id}</span>
          </span>
          <span className="source-title-text">{chunk.title || chunk.source_file}</span>
          {chunk.has_outdated_warning && (
            <span title="Contains outdated policy language" style={{ color: '#f59e0b', display: 'inline-flex' }}>
              <AlertTriangle size={13} />
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="source-score-pill">{scorePercent}% Match</span>
          {expanded ? <ChevronUp size={14} color="#94a3b8" /> : <ChevronDown size={14} color="#94a3b8" />}
        </div>
      </div>

      {expanded && (
        <div className="source-snippet-text">
          {chunk.snippet}
        </div>
      )}
    </div>
  );
}
