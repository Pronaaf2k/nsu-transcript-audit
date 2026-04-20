'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

const PROGRAMS = [
  'CSE',
  'BBA',
  'ETE',
  'ENV',
  'ENG',
  'ECO',
]

type UploadMode = 'csv' | 'ocr'

export default function ScanPage() {
  const supabase = createClient()
  const [program, setProgram] = useState('CSE')
  const [level, setLevel] = useState<'1' | '2' | '3'>('3')
  const [mode, setMode] = useState<UploadMode>('csv')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<unknown>(null)

  useEffect(() => {
    setError('')
    setResult(null)
  }, [mode])

  async function getToken(): Promise<string> {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) {
      throw new Error('Please log in first.')
    }
    return session.access_token
  }

  async function runAudit() {
    setError('')
    setResult(null)
    if (!file) {
      setError('Select a file first.')
      return
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) {
      setError('NEXT_PUBLIC_API_URL is not set.')
      return
    }

    setLoading(true)
    try {
      const token = await getToken()

      if (mode === 'csv') {
        const text = await file.text()
        const res = await fetch(`${apiUrl}/audit/run_csv`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            csv_text: text,
            program,
            audit_level: Number(level),
          }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          throw new Error(data?.detail || 'Audit failed')
        }
        setResult(data)
        return
      }

      const form = new FormData()
      form.append('file', file)
      form.append('program', program)
      form.append('audit_level', level)

      const res = await fetch(`${apiUrl}/audit/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.detail || 'OCR audit failed')
      }
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: 24, fontFamily: 'monospace' }}>
      <h1 style={{ marginBottom: 8 }}>NSU Web Audit</h1>
      <p style={{ marginBottom: 20, opacity: 0.8 }}>Only OCR/CSV + L1/L2/L3. No extra UI.</p>

      <div style={{ display: 'grid', gap: 12, marginBottom: 16 }}>
        <label>
          Program
          <select value={program} onChange={(e) => setProgram(e.target.value)} style={{ display: 'block', marginTop: 6, width: '100%', padding: 8 }}>
            {PROGRAMS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>

        <label>
          Audit Level
          <select value={level} onChange={(e) => setLevel(e.target.value as '1' | '2' | '3')} style={{ display: 'block', marginTop: 6, width: '100%', padding: 8 }}>
            <option value="1">Level 1</option>
            <option value="2">Level 2</option>
            <option value="3">Level 3</option>
          </select>
        </label>

        <label>
          Mode
          <select value={mode} onChange={(e) => setMode(e.target.value as UploadMode)} style={{ display: 'block', marginTop: 6, width: '100%', padding: 8 }}>
            <option value="csv">CSV</option>
            <option value="ocr">OCR (PDF/Image)</option>
          </select>
        </label>

        <label>
          File
          <input
            type="file"
            accept={mode === 'csv' ? '.csv,text/csv' : '.pdf,.png,.jpg,.jpeg,.webp'}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            style={{ display: 'block', marginTop: 6 }}
          />
        </label>

        <button onClick={runAudit} disabled={loading} style={{ padding: 10, cursor: loading ? 'not-allowed' : 'pointer' }}>
          {loading ? 'Running...' : 'Run Audit'}
        </button>
      </div>

      {error && <pre style={{ color: '#b91c1c', whiteSpace: 'pre-wrap' }}>{error}</pre>}

      {result && (
        <pre style={{ whiteSpace: 'pre-wrap', background: '#111827', color: '#e5e7eb', padding: 12, borderRadius: 8, overflowX: 'auto' }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </main>
  )
}
