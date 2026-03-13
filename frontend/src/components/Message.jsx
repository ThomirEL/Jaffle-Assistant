import React from 'react'
import ChartBlock from './ChartBlock.jsx'

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: 5, alignItems: 'center', padding: '4px 0' }}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--text-dim)',
            animation: 'pulse 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}

function TextContent({ text }) {
  // Render markdown-lite: bold, code blocks, line breaks
  const lines = text.split('\n')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {lines.map((line, i) => {
        if (!line.trim()) return <br key={i} />

        // Heading lines
        if (line.startsWith('### ')) return (
          <p key={i} style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, color: '#14b8a6', marginTop: 12 }}>
            {line.replace('### ', '')}
          </p>
        )
        if (line.startsWith('## ')) return (
          <p key={i} style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, color: '#6366f1', marginTop: 14 }}>
            {line.replace('## ', '')}
          </p>
        )

        // Bullet points
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent)', marginTop: 2, flexShrink: 0, fontWeight: 600 }}>›</span>
              <span>{renderInline(line.replace(/^[-*]\s/, ''))}</span>
            </div>
          )
        }

        return <p key={i}>{renderInline(line)}</p>
      })}
    </div>
  )
}

function renderInline(text) {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: '#14b8a6', fontWeight: 600 }}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} style={{
          background: 'rgba(99, 102, 241, 0.2)',
          padding: '2px 6px',
          borderRadius: 4,
          fontSize: 13,
          color: '#6366f1',
          fontWeight: 500,
        }}>
          {part.slice(1, -1)}
        </code>
      )
    }
    return part
  })
}

export default function Message({ message }) {
  const isUser = message.role === 'user'
  const isLoading = message.loading

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: isUser ? 'flex-end' : 'flex-start',
      gap: 10,
      animation: 'fadeSlideIn 0.3s ease forwards',
    }}>
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Role label */}
      <div style={{
        fontSize: 10,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: 'var(--text-dim)',
        fontWeight: 600,
        paddingLeft: isUser ? 0 : 2,
        paddingRight: isUser ? 2 : 0,
      }}>
        {isUser ? '👤 You' : '🤖 Jaffle AI'}
      </div>

      {/* Bubble */}
      <div style={{
        background: isUser 
          ? 'linear-gradient(135deg, rgba(102, 126, 234, 0.3), rgba(118, 75, 162, 0.25))'
          : 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(236, 72, 153, 0.05))',
        border: `1px solid ${isUser ? 'rgba(99, 102, 241, 0.4)' : 'var(--border)'}`,
        borderRadius: isUser
          ? 'var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)'
          : 'var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm)',
        padding: '16px 20px',
        color: 'var(--text-pri)',
        lineHeight: 1.7,
        width: isUser ? 'auto' : '100%',
        maxWidth: isUser ? '60%' : '100%',
        backdropFilter: 'blur(4px)',
        boxShadow: isUser 
          ? '0 4px 12px rgba(99, 102, 241, 0.2)' 
          : 'none',
      }}>
        {isLoading
          ? <TypingIndicator />
          : <TextContent text={message.text} />
        }

        {/* Error state */}
        {message.error && (
          <p style={{
            marginTop: 10,
            color: '#ff6b6b',
            fontSize: 12,
            fontStyle: 'italic',
            padding: '8px 12px',
            background: 'rgba(255, 107, 107, 0.1)',
            borderRadius: 'var(--radius-sm)',
            borderLeft: '2px solid #ff6b6b',
          }}>
            ⚠ {message.error}
          </p>
        )}
      </div>

      {/* Chart below the bubble, full width */}
      {!isUser && message.chart && (
        <div style={{ width: '100%' }}>
          <ChartBlock chart={message.chart} />
        </div>
      )}
    </div>
  )
}
