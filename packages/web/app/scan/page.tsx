'use client'

import { useEffect, useState, useRef } from 'react'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'
import AuditReport from '@/components/AuditReport'
import CourseEditor from '@/components/CourseEditor'
import { createClient } from '@/lib/supabase/client'

const FALLBACK_PROGRAMS = [
  { code: 'CSE', name: 'Computer Science & Engineering' },
  { code: 'BBA', name: 'Business Administration' },
  { code: 'ETE', name: 'Electronic & Telecom Engineering' },
  { code: 'ENV', name: 'Environmental Science & Management' },
  { code: 'ENG', name: 'English' },
  { code: 'ECO', name: 'Economics' },
]

const GRADE_POINTS: Record<string, number> = {
  'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
  'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}

interface ParsedCourse {
  course: string
  courseName: string
  credits: number
  grade: string
  semester: string
  gradePoints: number
}

function parseCSVToCourses(csvText: string): ParsedCourse[] {
  const lines = csvText.trim().split('\n')
  const rows: ParsedCourse[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.toLowerCase().includes('course_code')) continue
    const parts = trimmed.split(',').map(p => p.trim())
    if (parts.length >= 5) {
      const grade = parts[3]?.toUpperCase() || ''
      rows.push({
        course: parts[0] || '',
        courseName: parts[1] || '',
        credits: parseFloat(parts[2]) || 3,
        grade: grade,
        semester: parts[4] || 'Unknown',
        gradePoints: GRADE_POINTS[grade] ?? 0
      })
    }
  }
  return rows
}

type Mode = 'csv' | 'ocr'
type OcrStep = 'idle' | 'extracting' | 'review' | 'editing' | 'auditing' | 'done'

export default function ScanPage() {
  const supabase = createClient()
  const csvInputRef = useRef<HTMLInputElement>(null)
  const ocrInputRef = useRef<HTMLInputElement>(null)
  const [program, setProgram] = useState('')
  const [programs, setPrograms] = useState(FALLBACK_PROGRAMS)
  const [mode, setMode] = useState<Mode>('csv')

  // CSV mode
  const [csvLoading, setCsvLoading] = useState(false)
  const [csvError, setCsvError] = useState<string | null>(null)
  const [csvResult, setCsvResult] = useState<Record<string, unknown> | null>(null)
  const [csvText, setCsvText] = useState('')

  // OCR mode
  const [ocrStep, setOcrStep] = useState<OcrStep>('idle')
  const [ocrError, setOcrError] = useState<string | null>(null)
  const [extractedCsv, setExtractedCsv] = useState('')
  const [extractedCourses, setExtractedCourses] = useState<ParsedCourse[]>([])
  const [ocrResult, setOcrResult] = useState<Record<string, unknown> | null>(null)
  const [ocrFile, setOcrFile] = useState<File | null>(null)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) return

    fetch(`${apiUrl}/programs`)
      .then(res => res.ok ? res.json() : Promise.reject(new Error('Failed to load programs')))
      .then(data => {
        if (Array.isArray(data.programs) && data.programs.length > 0) {
          setPrograms(data.programs)
        }
      })
      .catch(() => {
        setPrograms(FALLBACK_PROGRAMS)
      })
  }, [])

  async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token
    if (!token) throw new Error('Please log in again.')
    return { Authorization: `Bearer ${token}` }
  }

  // ── CSV mode ──────────────────────────────────────────────────────────────
  async function handleCsvUpload(file: File) {
    if (!program) { setCsvError('Please select your program first'); return }
    setCsvError(null); setCsvLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) {
        throw new Error('NEXT_PUBLIC_API_URL is not set. Deploy the backend first.')
      }

      const text = await file.text()
      setCsvText(text)

      const authHeaders = await getAuthHeaders()
      const res = await fetch(`${apiUrl}/audit/run_csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ csv_text: text, program })
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Audit failed')
      }
      const result = await res.json()
      setCsvResult(result)
    } catch (e: unknown) {
      setCsvError(e instanceof Error ? e.message : String(e))
    } finally { setCsvLoading(false) }
  }

  // ── OCR mode ──────────────────────────────────────────────────────────────
  async function handleOcrUpload(file: File) {
    if (!program) { setOcrError('Please select your program first'); return }
    setOcrFile(file); setOcrError(null); setOcrStep('extracting')
    setExtractedCsv(''); setOcrResult(null); setExtractedCourses([])

    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (!apiUrl) {
      setOcrError('NEXT_PUBLIC_API_URL is not set. Deploy the backend first.')
      setOcrStep('idle'); return
    }

    try {
      const formData = new FormData()
      formData.append('file', file)
      const authHeaders = await getAuthHeaders()
      const res = await fetch(`${apiUrl}/audit/extract`, {
        method: 'POST',
        headers: authHeaders,
        body: formData,
        signal: AbortSignal.timeout(120000)
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Extraction failed')
      }
      const data = await res.json()
      const csvText = data.csv_text || ''
      setExtractedCsv(csvText)
      const courses = parseCSVToCourses(csvText)
      setExtractedCourses(courses)
      setOcrStep('review')
    } catch (e: unknown) {
      setOcrError(e instanceof Error ? e.message : String(e))
      setOcrStep('idle')
    }
  }

  function handleEditCourses() {
    setOcrStep('editing')
  }

  async function handleSaveEditedCourses(courses: ParsedCourse[], csvText: string) {
    setExtractedCourses(courses)
    setExtractedCsv(csvText)
    setOcrStep('review')
  }

  async function runOcrAudit() {
    if (!extractedCsv || !program) return
    setOcrStep('auditing'); setOcrError(null)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      const authHeaders = await getAuthHeaders()
      const res = await fetch(`${apiUrl}/audit/run_csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ csv_text: extractedCsv, program })
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Audit failed')
      }
      const data = await res.json()
      setOcrResult(data)

      setOcrStep('done')
    } catch (e: unknown) {
      setOcrError(e instanceof Error ? e.message : String(e))
      setOcrStep('review')
    }
  }

  function resetOcr() {
    setOcrStep('idle'); setExtractedCsv(''); setOcrResult(null); setOcrError(null); setOcrFile(null); setExtractedCourses([])
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px', borderRadius: 'var(--radius-sm)', fontWeight: 600,
    fontSize: '0.9rem', cursor: 'pointer', border: 'none', transition: 'all 0.15s',
    background: active ? 'var(--accent)' : 'var(--surface-2)',
    color: active ? '#fff' : 'var(--text-muted)',
  })

  return (
    <>
      <Nav />
      <div className="container">
        <div className="page-header">
          <h1>New Scan</h1>
          <p>Upload a transcript to run a graduation audit.</p>
        </div>

        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>
              1. Select Your Program <span style={{ color: 'var(--danger)' }}>*</span>
            </label>
            <select value={program} onChange={e => setProgram(e.target.value)}
              style={{ width: '100%', padding: '12px', fontSize: '1rem' }}>
              <option value="">-- Select your program --</option>
              {programs.map(p => <option key={p.code} value={p.code}>{p.name} ({p.code})</option>)}
            </select>
          </div>

          <div style={{ marginTop: '24px' }}>
            <label style={{ fontWeight: 600, marginBottom: '12px', display: 'block' }}>
              2. Choose Upload Method
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button style={tabStyle(mode === 'csv')} onClick={() => setMode('csv')}>
                📄 CSV Upload
              </button>
              <button style={tabStyle(mode === 'ocr')} onClick={() => setMode('ocr')}>
                🔍 OCR — PDF / Image
              </button>
            </div>
          </div>

          {/* ── CSV MODE ── */}
          {mode === 'csv' && (
            <div style={{ marginTop: '20px' }}>
              <div
                style={{
                  padding: '32px', border: `2px dashed ${program ? 'var(--border)' : 'var(--text-muted)'}`,
                  borderRadius: 'var(--radius)', opacity: program ? 1 : 0.5,
                  pointerEvents: program ? 'auto' : 'none', textAlign: 'center', cursor: 'pointer'
                }}
                onClick={() => csvInputRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleCsvUpload(f) }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}
                  style={{ width: '40px', height: '40px', color: 'var(--text-muted)', margin: '0 auto 12px' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p>Drag & drop a CSV file, or click to browse</p>
                <p style={{ fontSize: '0.8rem', marginTop: '4px', opacity: 0.7 }}>Format: Course_Code, Course_Name, Credits, Grade, Semester</p>
              </div>
              <input ref={csvInputRef} type="file" accept=".csv" style={{ display: 'none' }}
                onChange={e => { const f = e.target.files?.[0]; if (f) handleCsvUpload(f) }} />
              {csvLoading && (
                <div style={{ marginTop: '16px', padding: '14px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                  <p style={{ color: 'var(--accent)', fontWeight: 600 }}>Processing transcript...</p>
                </div>
              )}
              {csvError && <ErrorBox msg={csvError} />}
            </div>
          )}

          {/* ── OCR MODE ── */}
          {mode === 'ocr' && (
            <div style={{ marginTop: '20px' }}>
              {ocrStep === 'idle' && (
                <>
                  <div
                    style={{
                      padding: '32px', border: `2px dashed ${program ? 'var(--accent)' : 'var(--text-muted)'}`,
                      borderRadius: 'var(--radius)', opacity: program ? 1 : 0.5,
                      pointerEvents: program ? 'auto' : 'none', textAlign: 'center', cursor: 'pointer',
                      background: 'rgba(99,102,241,0.04)'
                    }}
                    onClick={() => ocrInputRef.current?.click()}
                    onDragOver={e => e.preventDefault()}
                    onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleOcrUpload(f) }}
                  >
                    <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🔍</div>
                    <p style={{ fontWeight: 600 }}>Drop a PDF or image transcript here</p>
                    <p style={{ fontSize: '0.8rem', marginTop: '6px', opacity: 0.7 }}>
                      Gemini 2.5 Flash will extract courses — you can review before auditing
                    </p>
                    <p style={{ fontSize: '0.75rem', marginTop: '4px', color: 'var(--accent)', opacity: 0.8 }}>
                      ⚡ Wake the backend first if it has been inactive
                    </p>
                  </div>
                  <input ref={ocrInputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp"
                    style={{ display: 'none' }}
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleOcrUpload(f) }} />
                  {ocrError && <ErrorBox msg={ocrError} />}
                </>
              )}

              {ocrStep === 'extracting' && (
                <div style={{ padding: '32px', textAlign: 'center', background: 'var(--surface-2)', borderRadius: 'var(--radius)' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '12px' }}>⏳</div>
                  <p style={{ color: 'var(--accent)', fontWeight: 700, fontSize: '1.1rem' }}>Extracting courses with Gemini...</p>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '6px' }}>
                    {ocrFile?.name} — this may take 15–30 seconds
                  </p>
                </div>
              )}

              {ocrStep === 'review' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <p style={{ fontWeight: 700, color: 'var(--accent)' }}>✅ {extractedCourses.length} courses extracted — review & edit</p>
                    <button onClick={resetOcr} style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-muted)', padding: '4px 10px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.8rem' }}>
                      ↩ Start Over
                    </button>
                  </div>
                  <textarea
                    value={extractedCsv}
                    onChange={e => setExtractedCsv(e.target.value)}
                    style={{
                      width: '100%', minHeight: '200px', fontFamily: 'monospace', fontSize: '0.82rem',
                      padding: '14px', background: 'var(--surface-2)', border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)', color: 'var(--text)', resize: 'vertical', boxSizing: 'border-box'
                    }}
                  />
                  <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                    <button onClick={handleEditCourses}
                      style={{ padding: '10px 20px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', fontWeight: 600, cursor: 'pointer' }}>
                      ✏️ Edit Courses Manually
                    </button>
                    <button onClick={runOcrAudit}
                      style={{ padding: '10px 28px', background: 'var(--success)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', fontWeight: 700, cursor: 'pointer' }}>
                      Run Audit →
                    </button>
                  </div>
                  {ocrError && <ErrorBox msg={ocrError} />}
                </div>
              )}

              {ocrStep === 'editing' && (
                <CourseEditor
                  initialCourses={extractedCourses}
                  onSave={handleSaveEditedCourses}
                  onCancel={() => setOcrStep('review')}
                />
              )}

              {ocrStep === 'auditing' && (
                <div style={{ padding: '24px', textAlign: 'center', background: 'var(--surface-2)', borderRadius: 'var(--radius)' }}>
                  <p style={{ color: 'var(--accent)', fontWeight: 700 }}>Running audit...</p>
                </div>
              )}

              {ocrStep === 'done' && (
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                  <button onClick={resetOcr}
                    style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-muted)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.85rem' }}>
                    ↩ New OCR Scan
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Results */}
        {csvResult && mode === 'csv' && (
          <div className="animate-in"><AuditReport scan={csvResult} csvText={csvText} /></div>
        )}
        {ocrResult && mode === 'ocr' && ocrStep === 'done' && (
          <div className="animate-in"><AuditReport scan={ocrResult} csvText={extractedCsv} /></div>
        )}
      </div>
      <Footer />
    </>
  )
}

function ErrorBox({ msg }: { msg: string }) {
  return (
    <div style={{ marginTop: '14px', padding: '12px 16px', background: 'rgba(244,63,94,0.1)', borderRadius: 'var(--radius-sm)', color: 'var(--danger)' }}>
      <strong>Error:</strong> {msg}
    </div>
  )
}
