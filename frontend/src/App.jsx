import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Menu, 
  X, 
  Sparkles, 
  ShieldCheck, 
  Clock, 
  RefreshCw, 
  Trash2, 
  AlertCircle,
  MessageSquareText,
  Copy,
  Check
} from 'lucide-react';
import Sidebar from './components/Sidebar';
import MessageBubble from './components/MessageBubble';
import HumanAgentModal from './components/HumanAgentModal';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

function getOrCreateSessionId() {
  const stored = localStorage.getItem('learnforge_session_id');
  if (stored) return stored;
  const newId = (typeof crypto !== 'undefined' && crypto.randomUUID) 
    ? crypto.randomUUID() 
    : 'sess-' + Math.random().toString(36).substring(2, 12);
  localStorage.setItem('learnforge_session_id', newId);
  return newId;
}

export default function App() {
  const [sessionId, setSessionId] = useState(getOrCreateSessionId);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [reingesting, setReingesting] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isHumanModalOpen, setIsHumanModalOpen] = useState(false);
  const [copiedSession, setCopiedSession] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Load session history on startup if any exists
  useEffect(() => {
    async function loadHistory() {
      try {
        const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.messages && data.messages.length > 0) {
            setMessages(data.messages.map(m => ({
              role: m.role,
              content: m.content,
            })));
          }
        }
      } catch (err) {
        // Backend may not be reachable immediately or session not found
      }
    }
    loadHistory();
  }, [sessionId]);

  // Handle Send Message
  const handleSend = async (textToSend) => {
    const text = (textToSend || inputValue).trim();
    if (!text || loading) return;

    // Add user message to state
    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      const assistantMsg = {
        role: 'assistant',
        content: data.answer,
        confidence: data.confidence,
        escalate: data.escalate,
        escalation_reason: data.escalation_reason,
        sources: data.sources || [],
        has_outdated_sources: data.has_outdated_sources,
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ **Connection Error:** Could not contact the LearnForge AI backend.\n\nDetails: \`${err.message}\`\n\nPlease ensure the FastAPI server is running on \`localhost:8000\`.`,
          confidence: 0.0,
          escalate: true,
          escalation_reason: 'Backend service communication failure',
          sources: [],
          has_outdated_sources: false,
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Start new clean session
  const handleNewSession = async () => {
    try {
      await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
    } catch (_) {}

    const newId = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : 'sess-' + Math.random().toString(36).substring(2, 12);
    localStorage.setItem('learnforge_session_id', newId);
    setSessionId(newId);
    setMessages([]);
    setSidebarOpen(false);
  };

  // Trigger Knowledge Base Reingestion
  const handleReingest = async () => {
    if (reingesting) return;
    setReingesting(true);
    try {
      const res = await fetch(`${API_BASE}/admin/reingest`, { method: 'POST' });
      const data = await res.json();
      alert(`Knowledge base re-indexed successfully!\n\n${data.chunks_inserted} chunks synchronized into Qdrant Cloud.`);
    } catch (err) {
      alert(`Re-ingestion failed: ${err.message}`);
    } finally {
      setReingesting(false);
    }
  };

  // Copy session ID
  const handleCopySession = () => {
    navigator.clipboard.writeText(sessionId);
    setCopiedSession(true);
    setTimeout(() => setCopiedSession(false), 2000);
  };

  // Auto-resize textarea
  const handleTextareaChange = (e) => {
    setInputValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-container">
      <div className="bg-ambient" />

      {/* Sidebar */}
      <Sidebar 
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSelectSample={(q) => {
          setSidebarOpen(false);
          handleSend(q);
        }}
        onNewSession={handleNewSession}
        onReingest={handleReingest}
        reingesting={reingesting}
      />

      {/* Main Chat Area */}
      <main className="chat-main">
        {/* Top Bar */}
        <header className="chat-topbar">
          <div className="topbar-left">
            <button 
              className="btn-ghost" 
              style={{ display: 'flex', padding: '6px 8px' }}
              onClick={() => setSidebarOpen(!sidebarOpen)}
              title="Toggle Knowledge Base & Models"
            >
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>

            <span className="topbar-title">LearnForge Support Assistant</span>
            
            <div className="live-indicator">
              <span className="live-dot" />
              <span>Qdrant + Gemini 3.5 Active</span>
            </div>
          </div>

          <div className="topbar-actions">
            <button 
              className="btn-ghost" 
              onClick={handleCopySession}
              title="Click to copy Session ID"
            >
              {copiedSession ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
              <span style={{ fontSize: '0.74rem' }}>
                {copiedSession ? 'Copied!' : `Session: ${sessionId.slice(0, 6)}...`}
              </span>
            </button>

            <button 
              className="btn-ghost"
              onClick={handleNewSession}
              title="Reset conversation"
            >
              <Trash2 size={13} />
              <span style={{ fontSize: '0.74rem' }}>Reset</span>
            </button>
          </div>
        </header>

        {/* Message Stream */}
        <div className="messages-viewport">
          {messages.length === 0 ? (
            <div className="messages-empty-state">
              <div className="empty-state-icon">
                <Sparkles size={30} />
              </div>
              <h1 className="empty-state-title">How can we assist you today?</h1>
              <p className="empty-state-desc">
                Ask about course access, certificates, refund terms, mobile offline downloads, 
                or billing. Every answer is grounded in our official knowledge base with verified 
                confidence scoring and automatic human escalation.
              </p>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center', marginTop: '12px' }}>
                <button 
                  className="btn-ghost"
                  onClick={() => handleSend('What is the refund policy for courses?')}
                >
                  Refund Policy (14 vs 7-day rule)
                </button>
                <button 
                  className="btn-ghost"
                  onClick={() => handleSend('Can I download videos for offline viewing on mobile?')}
                >
                  Mobile Offline Videos
                </button>
                <button 
                  className="btn-ghost"
                  onClick={() => handleSend('How do I request an invoice with company VAT?')}
                >
                  Tax Invoice Help
                </button>
                <button 
                  className="btn-ghost"
                  onClick={() => handleSend('How do I fix a flat tire on a bicycle?')}
                >
                  Out-of-Domain Escalation Test
                </button>
              </div>
            </div>
          ) : (
            messages.map((msg, index) => (
              <MessageBubble 
                key={index} 
                message={msg} 
                onEscalateClick={() => setIsHumanModalOpen(true)}
              />
            ))
          )}

          {/* Typing Indicator */}
          {loading && (
            <div className="typing-row">
              <div className="avatar-badge assistant">
                <Sparkles size={16} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.84rem' }}>Searching Qdrant & synthesizing answer...</span>
                <div className="typing-dots">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="chat-input-area">
          <div className="input-glass-container">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder="Ask anything about LearnForge courses, policies, or account issues..."
              value={inputValue}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              rows={1}
            />

            <div className="input-actions-bar">
              <div className="input-hint-text">
                Press <strong style={{ color: '#cbd5e1' }}>Enter</strong> to send, <strong style={{ color: '#cbd5e1' }}>Shift + Enter</strong> for newline
              </div>

              <button
                className="btn-send"
                onClick={() => handleSend()}
                disabled={loading || !inputValue.trim()}
                title="Send message"
                type="button"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Human Escalation Modal */}
      <HumanAgentModal 
        isOpen={isHumanModalOpen}
        onClose={() => setIsHumanModalOpen(false)}
        sessionId={sessionId}
      />
    </div>
  );
}
