'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'
import AuditReport from '@/components/AuditReport'

const PROGRAMS = [
  { code: 'CSE', name: 'Computer Science & Engineering (CSE)' },
  { code: 'BBA', name: 'Business Administration (BBA)' },
  { code: 'EEE', name: 'Electrical & Electronic Engineering (EEE)' },
  { code: 'ECE', name: 'Electronics & Computer Engineering (ECE)' },
  { code: 'ENG', name: 'English' },
  { code: 'ECO', name: 'Economics' },
  { code: 'ENV', name: 'Environmental Science' },
  { code: 'PHY', name: 'Physics' },
]

const GRADE_POINTS: Record<string, number> = {
  'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
  'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}

interface CourseRow {
  Course_Code: string
  Course_Name: string
  Credits: string
  Grade: string
  Semester: string
}

function parseCSV(csvText: string): CourseRow[] {
  const lines = csvText.trim().split('\n')
  const rows: CourseRow[] = []
  
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.toLowerCase().includes('course_code')) continue
    
    const parts = trimmed.split(',').map(p => p.trim())
    if (parts.length >= 5) {
      rows.push({
        Course_Code: parts[0] || '',
        Course_Name: parts[1] || '',
        Credits: parts[2] || '3',
        Grade: parts[3] || '',
        Semester: parts[4] || ''
      })
    }
  }
  return rows
}

function runAudit(courses: CourseRow[], program: string) {
  const passedBest: Record<string, number> = {}
  let totalCredits = 0
  const courseRows: { course: string; credits: number; grade: string; status: string }[] = []

  for (const row of courses) {
    const course = row.Course_Code.toUpperCase()
    const grade = row.Grade.toUpperCase()
    const credits = parseFloat(row.Credits) || 0
    const pts = GRADE_POINTS[grade]
    const isPassing = !['F', 'W', 'I', 'X'].includes(grade)

    if (isPassing) {
      if (!(course in passedBest)) {
        totalCredits += credits
        passedBest[course] = pts ?? 0
        courseRows.push({ course, credits, grade, status: 'Counted' })
      } else {
        courseRows.push({ course, credits, grade, status: pts && pts > passedBest[course] ? 'Retake (Ignored)' : 'Illegal Retake' })
        if (pts !== undefined && pts > passedBest[course]) {
          passedBest[course] = pts
        }
      }
    } else {
      const status = grade === 'W' ? 'Withdrawn' : grade === 'I' ? 'Incomplete' : 'Failed'
      courseRows.push({ course, credits, grade, status })
    }
  }

  return { totalCredits, courseRows, passedBest }
}

function runFullAudit(csvText: string, program: string) {
  const courses = parseCSV(csvText)
  if (courses.length === 0) {
    throw new Error('No valid course data found')
  }

  const l1 = runAudit(courses, program)
  
  const cgpa = Object.values(l1.passedBest).length > 0
    ? (Object.values(l1.passedBest).reduce((a, b) => a + b, 0) / Object.values(l1.passedBest).length)
    : 0

  return {
    level1: {
      totalCredits: l1.totalCredits,
      rows: l1.courseRows
    },
    level2: {
      cgpa: Math.round(cgpa * 100) / 100,
      gpaCredits: l1.totalCredits,
      standing: cgpa >= 2.0 ? 'NORMAL' : 'PROBATION'
    },
    level3: {
      eligible: cgpa >= 2.0 && l1.totalCredits >= 120,
      totalEarned: l1.totalCredits,
      cgpa: Math.round(cgpa * 100) / 100,
      totalRequired: 120,
      minCGPA: 2.0,
      missing: {},
      advisories: []
    },
    graduation_status: cgpa >= 2.0 && l1.totalCredits >= 120 ? 'PASS' : 'FAIL',
    total_credits: l1.totalCredits
  }
}

export default function ScanPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [program, setProgram] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  async function handleUpload(file: File) {
    if (!program) {
      setError('Please select your program first')
      return
    }
    
    setError(null)
    setLoading(true)
    
    try {
      const text = await file.text()
      const auditResult = runFullAudit(text, program)
      setResult(auditResult)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f && (f.name.endsWith('.csv') || f.type === 'text/csv')) {
      handleUpload(f)
    } else {
      setError('Please upload a CSV file')
    }
  }

  return (
    <>
      <Nav />
      <div className="container">
        <div className="page-header">
          <h1>New Scan</h1>
          <p>Upload a CSV transcript to run a graduation audit.</p>
        </div>

        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="form-group">
            <label htmlFor="program-select" style={{ fontWeight: 600, marginBottom: '8px', display: 'block' }}>
              1. Select Your Program <span style={{ color: 'var(--danger)' }}>*</span>
            </label>
            <select 
              id="program-select" 
              value={program} 
              onChange={e => setProgram(e.target.value)}
              style={{ width: '100%', padding: '12px', fontSize: '1rem' }}
            >
              <option value="">-- Select your program --</option>
              {PROGRAMS.map(p => (
                <option key={p.code} value={p.code}>{p.name}</option>
              ))}
            </select>
          </div>
          
          <div style={{ marginTop: '24px' }}>
            <label style={{ fontWeight: 600, marginBottom: '12px', display: 'block' }}>
              2. Upload Transcript CSV
            </label>
            <div 
              style={{ 
                padding: '24px', 
                border: `2px dashed ${program ? 'var(--border)' : 'var(--text-muted)'}`, 
                borderRadius: 'var(--radius)',
                opacity: program ? 1 : 0.5,
                pointerEvents: program ? 'auto' : 'none',
                textAlign: 'center',
                cursor: program ? 'pointer' : 'default'
              }}
              onClick={() => inputRef.current?.click()}
              onDragOver={e => e.preventDefault()}
              onDrop={handleDrop}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} style={{ width: '40px', height: '40px', color: 'var(--text-muted)', margin: '0 auto 12px' }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p>Drag & drop a CSV file, or click to browse</p>
              <p style={{ fontSize: '0.8rem', marginTop: '4px', opacity: 0.7 }}>Format: Course_Code, Course_Name, Credits, Grade, Semester</p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(f) }}
            />
          </div>
          
          {loading && (
            <div style={{ marginTop: '20px', padding: '16px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
              <p style={{ color: 'var(--accent)', fontWeight: 600 }}>Processing transcript...</p>
            </div>
          )}
          
          {error && (
            <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(244,63,94,0.1)', borderRadius: 'var(--radius-sm)', color: 'var(--danger)' }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {result && (
          <div className="animate-in">
            <AuditReport scan={result} />
          </div>
        )}
      </div>
      <Footer />
    </>
  )
}
