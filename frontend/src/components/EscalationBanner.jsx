import React from 'react';
import { UserCheck, ShieldAlert, ArrowRight } from 'lucide-react';

export default function EscalationBanner({ reason, onEscalateClick }) {
  return (
    <div className="escalation-banner">
      <div className="escalation-header">
        <ShieldAlert size={18} color="#ef4444" />
        <span>Human Support Escalation Recommended</span>
      </div>
      
      <p className="escalation-reason-text">
        {reason || 'The assistant could not identify a confident, authoritative match in the knowledge base.'}
      </p>

      <div className="escalation-actions">
        <button 
          className="btn-escalate-primary"
          onClick={onEscalateClick}
          type="button"
        >
          <UserCheck size={15} />
          <span>Connect with Support Agent</span>
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
