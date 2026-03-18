import React, { useState, useRef, useEffect } from 'react'
import Message from './components/Message.jsx'
import InputBar from './components/InputBar.jsx'

const WELCOME_TEXT = "Hi — I'm your Jaffle Shop data assistant.\n\nAsk me anything about **orders**, **products**, **customers**, or **revenue**. I'll query the database and show you the numbers, along with a chart when it helps."

let msgId = 0
const uid = () => `msg-${++msgId}`
let chatId = 0
const newChatId = () => ++chatId

function makeWelcomeMessage() {
  return { id: uid(), role: 'agent', text: WELCOME_TEXT, chart: null }
}

function makeNewChat(name = null) {
  const id = newChatId()
  return {
    id,
    name: name || `Chat ${id}`,
    messages: [makeWelcomeMessage()],
  }
}

export default function App() {
  const [chats, setChats] = useState([makeNewChat()])
  const [activeChatId, setActiveChatId] = useState(1)
  const [loading, setLoading] = useState(false)
  const [editingChatId, setEditingChatId] = useState(null)
  const [editingName, setEditingName] = useState("")
  const bottomRef = useRef(null)

  const activeChat = chats.find(c => c.id === activeChatId)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeChat?.messages])

  // ── Chat management ──────────────────────────────────────────────────────────

  const createNewChat = () => {
    const chat = makeNewChat()
    setChats(prev => [...prev, chat])
    setActiveChatId(chat.id)
  }

  const clearChat = () => {
    setChats(prev => prev.map(c =>
      c.id === activeChatId
        ? { ...c, messages: [makeWelcomeMessage()] }
        : c
    ))
  }

  const deleteChat = (id) => {
    setChats(prev => {
      const remaining = prev.filter(c => c.id !== id)
      if (remaining.length === 0) {
        const fresh = makeNewChat()
        setActiveChatId(fresh.id)
        return [fresh]
      }
      if (activeChatId === id) {
        setActiveChatId(remaining[remaining.length - 1].id)
      }
      return remaining
    })
  }

  const startRenaming = (chat) => {
    setEditingChatId(chat.id)
    setEditingName(chat.name)
  }

  const commitRename = () => {
    if (!editingName.trim()) return
    setChats(prev => prev.map(c =>
      c.id === editingChatId ? { ...c, name: editingName.trim() } : c
    ))
    setEditingChatId(null)
  }

  // ── Messaging ────────────────────────────────────────────────────────────────

  const buildHistory = (messages) => {
    // Convert messages to the format the backend expects
    // Skip the welcome message (first agent message)
    return messages
      .slice(1)
      .filter(m => !m.loading && m.text)
      .map(m => ({
        role: m.role === 'agent' ? 'assistant' : 'user',
        content: m.text,
      }))
  }

  const sendMessage = async (text) => {
    const userMsg = { id: uid(), role: 'user', text }
    const loadingMsg = { id: uid(), role: 'agent', loading: true, text: '', chart: null }

    // Capture history before adding new messages
    const history = buildHistory(activeChat.messages)

    setChats(prev => prev.map(c =>
      c.id === activeChatId
        ? { ...c, messages: [...c.messages, userMsg, loadingMsg] }
        : c
    ))
    setLoading(true)

    // Auto-name the chat after the first user message
    if (activeChat.messages.filter(m => m.role === 'user').length === 0) {
      const autoName = text.length > 30 ? text.slice(0, 30) + '…' : text
      setChats(prev => prev.map(c =>
        c.id === activeChatId ? { ...c, name: autoName } : c
      ))
    }

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      })

      if (res.status === 504) {
        setChats(prev => prev.map(c =>
          c.id === activeChatId
            ? {
                ...c,
                messages: c.messages.map(m =>
                  m.id === loadingMsg.id
                    ? { ...m, loading: false, text: "That query took too long. Try asking something more specific." }
                    : m
                )
              }
            : c
        ))
        return
      }

      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      const data = await res.json()

      setChats(prev => prev.map(c =>
        c.id === activeChatId
          ? {
              ...c,
              messages: c.messages.map(m =>
                m.id === loadingMsg.id
                  ? { ...m, loading: false, text: data.text || 'No response.', chart: data.chart || null }
                  : m
              )
            }
          : c
      ))
    } catch (err) {
      setChats(prev => prev.map(c =>
        c.id === activeChatId
          ? {
              ...c,
              messages: c.messages.map(m =>
                m.id === loadingMsg.id
                  ? { ...m, loading: false, text: 'Something went wrong.', error: err.message }
                  : m
              )
            }
          : c
      ))
    } finally {
      setLoading(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ── Sidebar ──────────────────────────────────────────────────────────── */}
      <aside style={{
        width: 220,
        flexShrink: 0,
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '28px 12px',
        gap: 16,
      }}>
        {/* Logo */}
        <div style={{ padding: '0 8px', marginBottom: 8 }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 800,
            fontSize: 18,
            color: 'var(--accent)',
            letterSpacing: '-0.02em',
            lineHeight: 1,
          }}>
            JAFFLE
          </div>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 400,
            fontSize: 11,
            color: 'var(--text-sec)',
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            marginTop: 3,
          }}>
            Data Assistant
          </div>
        </div>

        {/* New chat button */}
        <button
          onClick={createNewChat}
          style={{
            background: 'var(--accent)',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            color: '#000',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            fontWeight: 500,
            padding: '8px 12px',
            cursor: 'pointer',
            letterSpacing: '0.04em',
            textAlign: 'left',
          }}
        >
          + New Chat
        </button>

        {/* Chat list */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}>
          {chats.map(chat => (
            <div
              key={chat.id}
              onClick={() => setActiveChatId(chat.id)}
              style={{
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                background: chat.id === activeChatId ? 'var(--bg-input)' : 'transparent',
                border: chat.id === activeChatId ? '1px solid var(--border-hi)' : '1px solid transparent',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                group: true,
              }}
            >
              {editingChatId === chat.id ? (
                <input
                  autoFocus
                  value={editingName}
                  onChange={e => setEditingName(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={e => e.key === 'Enter' && commitRename()}
                  onClick={e => e.stopPropagation()}
                  style={{
                    flex: 1,
                    background: 'transparent',
                    border: 'none',
                    outline: 'none',
                    color: 'var(--text-pri)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 12,
                  }}
                />
              ) : (
                <span style={{
                  flex: 1,
                  fontSize: 12,
                  color: chat.id === activeChatId ? 'var(--accent)' : 'var(--text-sec)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {chat.name}
                </span>
              )}

              {/* Action buttons — only show on active chat */}
              {chat.id === activeChatId && (
                <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                  <button
                    onClick={e => { e.stopPropagation(); startRenaming(chat) }}
                    title="Rename"
                    style={iconBtnStyle}
                  >✎</button>
                  <button
                    onClick={e => { e.stopPropagation(); deleteChat(chat.id) }}
                    title="Delete"
                    style={{ ...iconBtnStyle, color: 'var(--error)' }}
                  >✕</button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Status */}
        <div style={{
          padding: '10px 10px',
          background: 'var(--bg-input)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: loading ? '#ffb247' : 'var(--success)',
              boxShadow: `0 0 6px ${loading ? '#ffb247' : 'var(--success)'}`,
              flexShrink: 0,
            }} />
            <span style={{ fontSize: 11, color: 'var(--text-sec)', letterSpacing: '0.04em' }}>
              {loading ? 'Thinking…' : 'Ready'}
            </span>
          </div>
          <div style={{ marginTop: 8, fontSize: 10, color: 'var(--text-dim)', lineHeight: 1.5 }}>
            Gemini 2.5 Flash<br />
            LangChain · DuckDB
          </div>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────────────── */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <header style={{
          borderBottom: '1px solid var(--border)',
          padding: '16px 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <div>
            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 16,
              color: 'var(--text-pri)',
              letterSpacing: '-0.01em',
            }}>
              {activeChat?.name || 'Chat'}
            </h1>
            <p style={{ fontSize: 11, color: 'var(--text-sec)', marginTop: 2 }}>
              {activeChat?.messages.filter(m => m.role === 'user').length} questions asked
            </p>
          </div>

          <button
            onClick={clearChat}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-sec)',
              fontSize: 11,
              padding: '6px 12px',
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              letterSpacing: '0.04em',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => {
              e.target.style.borderColor = 'var(--border-hi)'
              e.target.style.color = 'var(--text-pri)'
            }}
            onMouseLeave={e => {
              e.target.style.borderColor = 'var(--border)'
              e.target.style.color = 'var(--text-sec)'
            }}
          >
            Clear chat
          </button>
        </header>

        {/* Messages */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '28px',
          display: 'flex',
          flexDirection: 'column',
          gap: 24,
        }}>
          {activeChat?.messages.map(msg => (
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

const iconBtnStyle = {
  background: 'transparent',
  border: 'none',
  color: 'var(--text-dim)',
  cursor: 'pointer',
  fontSize: 11,
  padding: '2px 4px',
  lineHeight: 1,
  fontFamily: 'var(--font-mono)',
}