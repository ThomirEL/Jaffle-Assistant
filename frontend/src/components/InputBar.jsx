import React, { useRef, useEffect } from 'react'

const SUGGESTIONS = [
  'Top 5 products by revenue?',
  'How has order volume trended over time?',
  'Which customers have the highest lifetime value?',
  'What is our revenue breakdown by product category?',
]

export default function InputBar({ onSend, loading }) {
  const [value, setValue] = React.useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }, [value])

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || loading) return
    onSend(trimmed)
    setValue('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{
      borderTop: '1px solid var(--border)',
      background: 'linear-gradient(180deg, rgba(26, 26, 46, 0.5), rgba(15, 15, 30, 0.8))',
      backdropFilter: 'blur(10px)',
      padding: '20px 32px 32px',
    }}>
      {/* Suggestion chips */}
      <div style={{
        display: 'flex',
        gap: 10,
        flexWrap: 'wrap',
        marginBottom: 16,
      }}>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSend(s)}
            disabled={loading}
            style={{
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(20, 184, 166, 0.05))',
              border: '1px solid var(--border)',
              borderRadius: 24,
              padding: '6px 16px',
              color: 'var(--text-sec)',
              fontSize: 12,
              fontFamily: 'var(--font-mono)',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
              letterSpacing: '0.02em',
              whiteSpace: 'nowrap',
              fontWeight: 500,
              opacity: loading ? 0.5 : 1,
            }}
            onMouseEnter={e => {
              if (!loading) {
                e.target.style.borderColor = 'var(--accent)'
                e.target.style.color = 'var(--accent)'
                e.target.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(99, 102, 241, 0.1))'
              }
            }}
            onMouseLeave={e => {
              if (!loading) {
                e.target.style.borderColor = 'var(--border)'
                e.target.style.color = 'var(--text-sec)'
                e.target.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(20, 184, 166, 0.05))'
              }
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input row */}
      <div style={{
        display: 'flex',
        gap: 12,
        alignItems: 'flex-end',
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(236, 72, 153, 0.05))',
        border: '1px solid var(--border-hi)',
        borderRadius: 'var(--radius-lg)',
        padding: '12px 18px',
        transition: 'all 0.2s ease',
        boxShadow: '0 0 0 0 transparent',
      }}
        onFocusCapture={e => {
          e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.6)'
          e.currentTarget.style.boxShadow = '0 0 20px rgba(99, 102, 241, 0.15)'
        }}
        onBlurCapture={e => {
          e.currentTarget.style.borderColor = 'var(--border-hi)'
          e.currentTarget.style.boxShadow = '0 0 0 0 transparent'
        }}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask anything about Jaffle Shop data…"
          rows={1}
          disabled={loading}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-pri)',
            fontFamily: 'var(--font-mono)',
            fontSize: 14,
            lineHeight: 1.6,
            resize: 'none',
            overflowY: 'auto',
            opacity: loading ? 0.6 : 1,
          }}
        />

        <button
          onClick={handleSend}
          disabled={loading || !value.trim()}
          style={{
            flexShrink: 0,
            width: 38,
            height: 38,
            borderRadius: 'var(--radius-md)',
            border: 'none',
            background: loading || !value.trim() 
              ? 'rgba(107, 114, 128, 0.2)' 
              : 'linear-gradient(135deg, var(--accent), #ec4899)',
            color: loading || !value.trim() ? 'var(--text-dim)' : '#fff',
            cursor: loading || !value.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            fontSize: 16,
            fontWeight: 600,
            boxShadow: (loading || !value.trim()) ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.3)',
          }}
          onMouseEnter={e => {
            if (!loading && value.trim()) {
              e.target.style.transform = 'translateY(-2px)'
              e.target.style.boxShadow = '0 8px 20px rgba(99, 102, 241, 0.4)'
            }
          }}
          onMouseLeave={e => {
            e.target.style.transform = 'translateY(0)'
            if (!loading && value.trim()) {
              e.target.style.boxShadow = '0 4px 12px rgba(99, 102, 241, 0.3)'
            }
          }}
        >
          {loading ? '⏳' : '↑'}
        </button>
      </div>

      <p style={{
        textAlign: 'center',
        color: 'var(--text-dim)',
        fontSize: 11,
        marginTop: 12,
        letterSpacing: '0.06em',
        fontWeight: 500,
      }}>
        ⏎ Enter · ⇧ Enter for new line
      </p>
    </div>
  )
}
