import React from 'react';
import { X, CheckCircle2, UserCheck, Clock, MessageSquare, ShieldCheck } from 'lucide-react';

export default function HumanAgentModal({ isOpen, onClose, sessionId }) {
  if (!isOpen) return null;

  const ticketId = `LF-${Math.floor(10000 + Math.random() * 90000)}`;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <UserCheck size={20} color="#6366f1" />
            <span>Escalating to Live Support</span>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '8px',
            padding: '12px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <CheckCircle2 size={20} color="#10b981" />
            <div>
              <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#34d399' }}>
                Handoff Ticket Created
              </div>
              <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Ticket ID: <strong style={{ color: '#fff' }}>{ticketId}</strong> (Session: {sessionId.slice(0, 8)}...)
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#cbd5e1' }}>
              <Clock size={16} color="#06b6d4" />
              <span>Estimated wait time: <strong>&lt; 2 minutes</strong></span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#cbd5e1' }}>
              <MessageSquare size={16} color="#8b5cf6" />
              <span>Full chat history and retrieved context transferred</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#cbd5e1' }}>
              <ShieldCheck size={16} color="#10b981" />
              <span>Assigned to: <strong>Tier 2 Ed-Tech Specialist</strong></span>
            </div>
          </div>

          <p style={{ fontSize: '0.8rem', color: '#64748b', lineHeight: 1.4 }}>
            A human customer support representative has been notified and will take over this thread shortly.
          </p>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
          <button 
            className="btn-ghost" 
            style={{ background: 'var(--bg-surface-elevated)', color: '#fff' }}
            onClick={onClose}
          >
            Close & Return to Chat
          </button>
        </div>
      </div>
    </div>
  );
}
