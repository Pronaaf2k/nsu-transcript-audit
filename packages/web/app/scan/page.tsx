'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

const PROGRAMS = [
  { code: 'CSE', label: 'CSE' },
  { code: 'BBA', label: 'BBA (2014+)' },
  { code: 'BBA-OLD', label: 'BBA-OLD (pre-2014)' },
  { code: 'ETE', label: 'ETE' },
  { code: 'ENV', label: 'ENV' },
  { code: 'ENG', label: 'ENG' },
  { code: 'ECO', label: 'ECO' },
]

type UploadMode = 'csv' | 'ocr'

type HistoryRow = {
  id: string
  created_at: string
  program: string
  total_credits: number | null
  cgpa: number | null
  graduation_status: string
}

type AnyRecord = Record<string, any>

export default function ScanPage() {
  const supabase = createClient()
  const [userEmail, setUserEmail] = useState('')
  const [program, setProgram] = useState('CSE')
  const [level, setLevel] = useState<'1' | '2' | '3'>('3')
  const [mode, setMode] = useState<UploadMode>('csv')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<unknown>(null)
  const [historyRows, setHistoryRows] = useState<HistoryRow[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  useEffect(() => {
    let mounted = true
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return
      setUserEmail(data.session?.user?.email ?? '')
      if (data.session?.access_token) {
        void loadHistory(data.session.access_token)
      }
    })
    return () => {
      mounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [supabase])

  async function getToken() {
    const {
      data: { session },
    } = await supabase.auth.getSession()
    if (!session?.access_token) throw new Error('Please log in first.')
    return session.access_token
  }

  async function signOut() {
    await supabase.auth.signOut()
    location.href = '/'
  }

  async function loadHistory(existingToken?: string) {
    setHistoryLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) throw new Error('NEXT_PUBLIC_API_URL is not set.')
      const token = existingToken ?? (await getToken())
      const res = await fetch(`${apiUrl}/history?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const rows = await res.json().catch(() => [])
      if (!res.ok) throw new Error(rows?.detail || 'Failed to load history')
      setHistoryRows(Array.isArray(rows) ? rows : [])
    } catch {
      setHistoryRows([])
    } finally {
      setHistoryLoading(false)
    }
  }

  function normalizeReport(raw: unknown) {
    const r = (raw ?? {}) as AnyRecord
    const audit = (r.audit_result ?? {}) as AnyRecord
    const gradtrace = (audit.gradtrace ?? {}) as AnyRecord
    const level2 = (gradtrace.level_2 ?? audit.l2 ?? {}) as AnyRecord
    const level3 = (gradtrace.level_3 ?? audit.l3 ?? {}) as AnyRecord
    const missing = (level3.missing ?? {}) as Record<string, string[]>

    let missingCount = 0
    Object.values(missing).forEach((items) => {
      if (Array.isArray(items)) missingCount += items.length
    })

    return {
      id: String(r.id ?? ''),
      program: String(r.program_used ?? r.program ?? ''),
      programRequested: String(r.program_requested ?? ''),
      programInferenceConfidence: Number(r.program_inference_confidence ?? 0),
      auditLevel: Number(r.audit_level ?? 3),
      standing: String(level2.standing ?? 'UNKNOWN'),
      graduationStatus: String(r.graduation_status ?? audit.graduation_status ?? 'PENDING'),
      cgpa: Number(r.cgpa ?? level2.cgpa ?? 0),
      credits: Number(r.total_credits ?? audit.l1?.total_credits ?? 0),
      requiredCredits: Number(level3.total_credits_required ?? 0),
      missing,
      missingCount,
      raw: r,
    }
  }

  function statusColor(status: string) {
    const s = status.toUpperCase()
    if (s === 'PASS' || s === 'NORMAL') return '#86efac'
    if (s === 'FAIL') return '#fda4af'
    return '#bfdbfe'
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
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ csv_text: text, program, audit_level: Number(level) }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data?.detail || 'Audit failed')
        setResult(data)
        await loadHistory(token)
      } else {
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
        if (!res.ok) throw new Error(data?.detail || 'OCR audit failed')
        setResult(data)
        await loadHistory(token)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  function exportStandingCsv(raw: unknown) {
    const report = normalizeReport(raw)
    const semesters = report.raw?.audit_result?.gradtrace?.level_2?.semesters
    if (!Array.isArray(semesters) || semesters.length === 0) return

    const lines = ['Semester,TGPA,CGPA,Credits']
    semesters.forEach((s: AnyRecord) => {
      lines.push(`${s.semester ?? ''},${s.tgpa ?? ''},${s.cgpa ?? ''},${s.credits ?? ''}`)
    })

    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit-standing.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportOcrCsv(raw: unknown) {
    const report = normalizeReport(raw)
    const csvText = String(report.raw?.csv_text ?? '').trim()
    if (!csvText) return

    const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'ocr-extracted-transcript.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const report = result ? normalizeReport(result) : null

  return (
    <main style={{ minHeight: '100vh', background: '#060709', color: '#e7e1d8' }}>
      <header
        style={{
          borderBottom: '1px solid #1f2228',
          background: 'rgba(6,7,9,0.96)',
          position: 'sticky',
          top: 0,
          zIndex: 20,
        }}
      >
        <div
          style={{
            maxWidth: 1180,
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ fontFamily: 'Georgia, Times New Roman, serif', fontSize: 30, fontWeight: 600 }}>
            NSU Audit
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
            <span style={{ color: '#a8a095', fontSize: 13 }}>{userEmail}</span>
            <button
              onClick={signOut}
              style={{
                border: '1px solid #33373f',
                background: '#111319',
                color: '#e7e1d8',
                borderRadius: 8,
                padding: '8px 12px',
                cursor: 'pointer',
                fontWeight: 700,
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '38px 24px 56px' }}>
        <h1 style={{ margin: 0, fontSize: 42, fontFamily: 'Georgia, Times New Roman, serif', fontWeight: 600 }}>New Audit</h1>

        <section
          style={{
            marginTop: 18,
            border: '1px solid #1f2228',
            borderRadius: 12,
            background: '#0a0b0f',
            padding: 18,
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
              gap: 12,
              marginBottom: 14,
            }}
          >
            <label>
              <div style={{ color: '#b1aba1', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>Program</div>
              <select
                value={program}
                onChange={(e) => setProgram(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #2a2d33', background: '#111319', color: '#ece7df' }}
              >
              {PROGRAMS.map((p) => (
                <option key={p.code} value={p.code}>{p.label}</option>
              ))}
            </select>
          </label>

            <label>
              <div style={{ color: '#b1aba1', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>Audit Level</div>
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value as '1' | '2' | '3')}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #2a2d33', background: '#111319', color: '#ece7df' }}
              >
                <option value="1">Level 1</option>
                <option value="2">Level 2</option>
                <option value="3">Level 3</option>
              </select>
            </label>

            <label>
              <div style={{ color: '#b1aba1', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>Mode</div>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as UploadMode)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #2a2d33', background: '#111319', color: '#ece7df' }}
              >
                <option value="csv">Run CSV Audit</option>
                <option value="ocr">Scan OCR (PDF/Image)</option>
              </select>
            </label>

            <label>
              <div style={{ color: '#b1aba1', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>Transcript File</div>
              <input
                type="file"
                accept={mode === 'csv' ? '.csv,text/csv' : '.pdf,.png,.jpg,.jpeg,.webp'}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #2a2d33', background: '#111319', color: '#ece7df' }}
              />
            </label>
          </div>

          <button
            onClick={runAudit}
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px 14px',
              borderRadius: 8,
              border: '1px solid #3b404a',
              background: loading ? '#1b1f26' : '#ece7df',
              color: loading ? '#bfb7ac' : '#101216',
              fontWeight: 800,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Running Audit...' : 'Run Audit'}
          </button>
        </section>

        {error && (
          <div style={{ marginTop: 12, border: '1px solid #7f1d1d', background: '#1c0d0d', borderRadius: 10, padding: 12, color: '#fda4af' }}>
            {error}
          </div>
        )}

        {report && (
          <section style={{ marginTop: 18 }}>
            <div
              style={{
                border: '1px solid #1f2228',
                borderRadius: 12,
                background: '#0a0b0f',
                padding: 14,
                marginBottom: 12,
              }}
            >
              <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 14, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#b1aba1' }}>
                Audit Snapshot
              </h2>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
                  <tbody>
                    {[
                      ['Status', report.graduationStatus],
                      ['Program', report.program || '-'],
                      ['Audit Level', `L${report.auditLevel}`],
                      ['Credits', String(report.credits)],
                      ['CGPA', report.cgpa.toFixed(2)],
                      ['Scan ID', report.id || '-'],
                    ].map(([k, v]) => (
                      <tr key={String(k)} style={{ borderBottom: '1px solid #171b21' }}>
                        <td style={{ width: 180, color: '#9f988d', padding: '8px 6px', textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: 12 }}>{k}</td>
                        <td style={{ padding: '8px 6px', color: k === 'Status' ? statusColor(String(v)) : '#ece7df', fontWeight: 700 }}>{v}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {report.programRequested && report.programRequested !== report.program && (
                <p style={{ marginTop: 10, marginBottom: 0, color: '#fbbf24', fontSize: 13 }}>
                  OCR auto-switched program from <strong>{report.programRequested}</strong> to <strong>{report.program}</strong>
                  {' '}({Math.round(report.programInferenceConfidence * 100)}% confidence).
                </p>
              )}
            </div>

            <div
              style={{
                border: '1px solid #1f2228',
                borderRadius: 12,
                background: '#0a0b0f',
                padding: 18,
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                alignItems: 'center',
                gap: 12,
              }}
            >
              <div>
                <div
                  style={{
                    fontFamily: 'Georgia, Times New Roman, serif',
                    fontSize: 58,
                    lineHeight: 0.95,
                    color: statusColor(report.graduationStatus),
                  }}
                >
                  {report.graduationStatus === 'PASS' ? 'Eligible' : report.graduationStatus === 'FAIL' ? 'Not Eligible' : 'Pending'}
                </div>
                <div style={{ color: '#bbb3a8', marginTop: 8 }}>for graduation</div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ color: '#bbb3a8', letterSpacing: '0.08em', textTransform: 'uppercase', fontSize: 12 }}>CGPA</div>
                <div style={{ fontSize: 46, fontFamily: 'Georgia, Times New Roman, serif' }}>{report.cgpa.toFixed(2)}</div>
                <div style={{ color: '#bbb3a8' }}>{report.credits} / {report.requiredCredits || '-'} credits</div>
              </div>
            </div>

            <div style={{ marginTop: 12, border: '1px solid #1f2228', borderRadius: 12, background: '#0a0b0f', padding: 18 }}>
              <h2 style={{ marginTop: 0, marginBottom: 10, fontSize: 16, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#b1aba1' }}>Student Standing</h2>
              <div style={{ display: 'grid', gap: 6 }}>
                <div>Academic standing: <strong style={{ color: statusColor(report.standing) }}>{report.standing}</strong></div>
                <div>Missing courses: <strong>{report.missingCount}</strong></div>
              </div>

              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {Object.entries(report.missing).map(([group, items]) => (
                  <div key={group} style={{ border: '1px solid #262a31', borderRadius: 8, padding: '8px 10px' }}>
                    <strong style={{ color: '#d9d2c8' }}>{group}:</strong>{' '}
                    <span style={{ color: '#bbb3a8' }}>{Array.isArray(items) && items.length > 0 ? items.join(', ') : 'None'}</span>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 12 }}>
                {String(report.raw?.csv_text ?? '').trim() && (
                  <button
                    onClick={() => exportOcrCsv(result)}
                    style={{ border: '1px solid #2f5663', background: '#17313a', color: '#d8f4ff', borderRadius: 8, padding: '8px 11px', fontWeight: 700, cursor: 'pointer' }}
                  >
                    Download OCR CSV
                  </button>
                )}
                <button
                  onClick={() => exportStandingCsv(result)}
                  style={{ border: '1px solid #37436b', background: '#1d2751', color: '#dbe7ff', borderRadius: 8, padding: '8px 11px', fontWeight: 700, cursor: 'pointer' }}
                >
                  Export Standing CSV
                </button>
                <details>
                  <summary style={{ cursor: 'pointer', color: '#b6aea3' }}>Show raw JSON</summary>
                  <pre style={{ marginTop: 8, background: '#0f1218', border: '1px solid #242830', borderRadius: 8, padding: 10, overflowX: 'auto', color: '#d2d8e3' }}>
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </details>
              </div>
            </div>
          </section>
        )}

        <section style={{ marginTop: 18, border: '1px solid #1f2228', borderRadius: 12, background: '#0a0b0f', padding: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h2 style={{ margin: 0, fontSize: 16, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#b1aba1' }}>
              History
            </h2>
            <button
              onClick={() => void loadHistory()}
              disabled={historyLoading}
              style={{ border: '1px solid #2e333b', background: '#12151b', color: '#d7d0c6', borderRadius: 8, padding: '7px 10px', fontWeight: 700, cursor: 'pointer' }}
            >
              {historyLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {!historyLoading && historyRows.length === 0 ? (
            <div style={{ color: '#a9a196' }}>No transcript checked yet.</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #21252c', color: '#aba398', textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: 12 }}>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Date</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Program</th>
                    <th style={{ textAlign: 'right', padding: '8px 6px' }}>Credits</th>
                    <th style={{ textAlign: 'right', padding: '8px 6px' }}>CGPA</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Status</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>ID</th>
                  </tr>
                </thead>
                <tbody>
                  {historyRows.map((row) => (
                    <tr key={row.id} style={{ borderBottom: '1px solid #171b21' }}>
                      <td style={{ padding: '9px 6px' }}>{(row.created_at || '').slice(0, 10)}</td>
                      <td style={{ padding: '9px 6px' }}>{row.program}</td>
                      <td style={{ padding: '9px 6px', textAlign: 'right' }}>{row.total_credits ?? '-'}</td>
                      <td style={{ padding: '9px 6px', textAlign: 'right' }}>{row.cgpa ?? '-'}</td>
                      <td style={{ padding: '9px 6px', color: statusColor(row.graduation_status || '') }}>{row.graduation_status || '-'}</td>
                      <td style={{ padding: '9px 6px', color: '#9caec4', fontSize: 12 }}>{row.id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
