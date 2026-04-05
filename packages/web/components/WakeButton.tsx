'use client'

import { useState } from 'react'

export default function WakeButton() {
  const [status, setStatus] = useState<'idle' | 'waking' | 'awake' | 'error'>('idle')

  const wake = async () => {
    setStatus('waking')
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) {
      setStatus('error')
      return
    }
    try {
      const res = await fetch(`${apiUrl}/health`)
      if (res.ok) setStatus('awake')
      else setStatus('error')
    } catch {
      setStatus('error')
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'idle': return 'var(--surface-2)'
      case 'waking': return 'rgba(251, 191, 36, 0.2)'
      case 'awake': return 'rgba(34, 197, 94, 0.2)'
      case 'error': return 'rgba(244, 63, 94, 0.2)'
    }
  }

  const getBorderColor = () => {
    switch (status) {
      case 'idle': return 'var(--border)'
      case 'waking': return '#fbbf24'
      case 'awake': return 'var(--success)'
      case 'error': return 'var(--danger)'
    }
  }

  const getText = () => {
    switch (status) {
      case 'idle': return '⚡ Wake Backend'
      case 'waking': return '⏳ Starting...'
      case 'awake': return '✅ Backend Ready'
      case 'error': return '❌ Failed - Retry'
    }
  }

  return (
    <button
      onClick={wake}
      disabled={status === 'waking'}
      style={{
        padding: '10px 20px',
        borderRadius: 'var(--radius)',
        border: `1px solid ${getBorderColor()}`,
        background: getStatusColor(),
        color: status === 'idle' ? 'var(--text)' : status === 'waking' ? '#fbbf24' : status === 'awake' ? 'var(--success)' : 'var(--danger)',
        cursor: status === 'waking' ? 'wait' : 'pointer',
        fontSize: '0.9rem',
        fontWeight: 600,
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}
    >
      {status === 'waking' && (
        <span style={{
          display: 'inline-block',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          background: '#fbbf24',
          animation: 'pulse 1s infinite'
        }} />
      )}
      {getText()}
    </button>
  )
}
