import React, { useState, useRef, useEffect } from 'react'
import Message from './components/Message.jsx'
import InputBar from './components/InputBar.jsx'

const WELCOME = {
  id: 'welcome',
  role: 'agent',
  text: "Hi — I'm your Jaffle Shop data assistant.\n\nAsk me anything about **orders**, **products**, **customers**, or **revenue**. I'll query the database and show you the numbers, along with a chart when it helps.",
  chart: null,
}

let msgId = 0
const uid = () => `msg-${++msgId}`

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    const userMsg = { id: uid(), role: 'user', text }
    const loadingMsg = { id: uid(), role: 'agent', loading: true, text: '', chart: null }

    setMessages(prev => [...prev, userMsg, loadingMsg])
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })

      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      const data = await res.json()

      setMessages(prev =>
        prev.map(m =>
          m.id === loadingMsg.id
            ? { ...m, loading: false, text: data.text || 'No response.', chart: data.chart || null }
            : m
        )
      )
    } catch (err) {
      setMessages(prev =>
        prev.map(m =>
          m.id === loadingMsg.id
            ? { ...m, loading: false, text: 'Something went wrong.', error: err.message }
            : m
        )
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
    }}>
      <style>{`
        @keyframes gradient-shift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        .sidebar-gradient {
          background: linear-gradient(-45deg, rgba(99, 102, 241, 0.15), rgba(236, 72, 153, 0.1), rgba(20, 184, 166, 0.1));
          background-size: 400% 400%;
          animation: gradient-shift 8s ease infinite;
        }
      `}</style>
      {/* ── Sidebar ──────────────────────────────────────────────── */}
      <aside className="sidebar-gradient" style={{
        width: 260,
        flexShrink: 0,
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '32px 24px',
        gap: 28,
        backdropFilter: 'blur(10px)',
      }}>
        {/* Logo */}
        <div>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 800,
            fontSize: 22,
            background: 'linear-gradient(135deg, #6366f1, #ec4899)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            letterSpacing: '-0.02em',
            lineHeight: 1,
          }}>
            JAFFLE
          </div>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: 10,
            color: 'var(--text-sec)',
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            marginTop: 6,
            fontWeight: 500,
          }}>
            Data AI Assistant
          </div>
        </div>

        {/* Nav items */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {[
            { label: 'Chat', active: true },
          ].map(item => (
            <div
              key={item.label}
              style={{
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: item.active 
                  ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(236, 72, 153, 0.2))'
                  : 'transparent',
                border: item.active ? '1px solid var(--border-hi)' : '1px solid transparent',
                color: item.active ? 'var(--text-pri)' : 'var(--text-sec)',
                fontSize: 13,
                fontWeight: item.active ? 600 : 400,
                cursor: 'pointer',
                letterSpacing: '0.04em',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                if (!item.active) {
                  e.currentTarget.style.background = 'rgba(99, 102, 241, 0.1)'
                  e.currentTarget.style.borderColor = 'var(--border-hi)'
                  e.currentTarget.style.color = 'var(--text-pri)'
                }
              }}
              onMouseLeave={e => {
                if (!item.active) {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.borderColor = 'transparent'
                  e.currentTarget.style.color = 'var(--text-sec)'
                }
              }}
            >
              {item.label}
            </div>
          ))}
        </nav>

        {/* Status */}
        <div style={{ marginTop: 'auto' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '12px 14px',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(20, 184, 166, 0.1))',
            border: '1px solid var(--border-hi)',
            borderRadius: 'var(--radius-md)',
            transition: 'all 0.3s ease',
          }}>
            <div style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: loading ? '#ffb247' : 'var(--success)',
              boxShadow: `0 0 10px ${loading ? '#ffb247' : 'var(--success)'}`,
              flexShrink: 0,
              animation: loading ? 'pulse 1.2s ease-in-out infinite' : 'none',
            }} />
            <span style={{ fontSize: 12, color: 'var(--text-pri)', letterSpacing: '0.04em', fontWeight: 500 }}>
              {loading ? 'Thinking…' : 'Ready'}
            </span>
          </div>

          <div style={{
            marginTop: 16,
            fontSize: 10,
            color: 'var(--text-dim)',
            lineHeight: 1.7,
            letterSpacing: '0.04em',
          }}>
            Powered by<br />
            <span style={{ color: 'var(--accent)', fontWeight: 500 }}>Gemini 2.5 Flash</span><br />
            <span style={{ color: 'var(--text-sec)', fontSize: 9 }}>LangChain · DuckDB</span>
          </div>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────── */}
      <main style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--bg)',
      }}>
        {/* Header */}
        <header style={{
          borderBottom: '1px solid var(--border)',
          padding: '20px 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          backdropFilter: 'blur(10px)',
          background: 'linear-gradient(180deg, rgba(15, 15, 30, 0.8), rgba(26, 26, 46, 0.5))',
        }}>
          <div>
            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 18,
              color: 'var(--text-pri)',
              letterSpacing: '-0.01em',
            }}>
              Business Intelligence Chat
            </h1>
            <p style={{ fontSize: 12, color: 'var(--text-sec)', marginTop: 4, letterSpacing: '0.04em' }}>
              Ask questions about your data in plain English
            </p>
          </div>

          <button
            onClick={() => setMessages([WELCOME])}
            style={{
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.15))',
              border: '1px solid var(--border-hi)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-sec)',
              fontSize: 12,
              padding: '8px 16px',
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              letterSpacing: '0.04em',
              transition: 'all 0.2s ease',
              fontWeight: 500,
            }}
            onMouseEnter={e => {
              e.target.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(236, 72, 153, 0.25))'
              e.target.style.borderColor = 'rgba(99, 102, 241, 0.5)'
              e.target.style.color = 'var(--text-pri)'
            }}
            onMouseLeave={e => {
              e.target.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.15))'
              e.target.style.borderColor = 'var(--border-hi)'
              e.target.style.color = 'var(--text-sec)'
            }}
          >
            ✕ Clear chat
          </button>
        </header>

        {/* Messages */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '32px 40px',
          display: 'flex',
          flexDirection: 'column',
          gap: 24,
        }}>
          {messages.map(msg => (
            <Message key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <InputBar onSend={sendMessage} loading={loading} />
      </main>
    </div>
  )
}
