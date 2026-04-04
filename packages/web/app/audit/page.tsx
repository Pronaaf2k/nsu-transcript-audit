'use client'

import { useState, useRef } from 'react'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'

const PROGRAMS = [
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

interface CourseRow {
  Course_Code: string
  Course_Name: string
  Credits: string
  Grade: string
  Semester: string
}

interface SemesterData {
  semester: string
  courses: { course: string; credits: number; grade: string; status: string }[]
  tgpa: number
  cgpa: number
  semCredits: number
  status: 'normal' | 'probation'
}

interface AuditResult {
  level1: {
    totalCredits: number
    rows: { course: string; credits: number; grade: string; status: string }[]
  }
  level2: {
    cgpa: number
    gpaCredits: number
    semesters: SemesterData[]
    standing: string
    consecutiveProbation: number
  }
  level3: {
    eligible: boolean
    totalEarned: number
    cgpa: number
    totalRequired: number
    minCGPA: number
    missing: Record<string, string[]>
    advisories: string[]
    invalidElectives: string[]
  }
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

function semesterSortKey(sem: string): [number, number] {
  const parts = sem.trim().split(/\s+/)
  if (parts.length === 2) {
    const seasonOrder: Record<string, number> = { Spring: 0, Summer: 1, Fall: 2 }
    const season = parts[0]
    const year = parseInt(parts[1])
    if (!isNaN(year) && season in seasonOrder) {
      return [year, seasonOrder[season]]
    }
  }
  return [9999, 99]
}

function runLevel1(courses: CourseRow[]) {
  const passedBest: Record<string, number> = {}
  const rows: { course: string; credits: number; grade: string; status: string }[] = []
  let totalCredits = 0

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
        rows.push({ course, credits, grade, status: 'Counted' })
      } else {
        if (passedBest[course] >= 3.3) {
          rows.push({ course, credits, grade, status: 'Illegal Retake' })
        } else {
          rows.push({ course, credits, grade, status: 'Retake (Ignored)' })
        }
        if (pts !== undefined && pts > passedBest[course]) {
          passedBest[course] = pts
        }
      }
    } else {
      const status = grade === 'W' ? 'Withdrawn' : grade === 'I' ? 'Incomplete' : 'Failed'
      rows.push({ course, credits, grade, status })
    }
  }

  return { totalCredits, rows }
}

function runLevel2(courses: CourseRow[]) {
  const semesterMap: Record<string, CourseRow[]> = {}
  
  for (const row of courses) {
    const sem = row.Semester || 'Unknown'
    if (!semesterMap[sem]) semesterMap[sem] = []
    semesterMap[sem].push(row)
  }

  const sortedSems = Object.keys(semesterMap).sort((a, b) => {
    const [aYear, aSeason] = semesterSortKey(a)
    const [bYear, bSeason] = semesterSortKey(b)
    return aYear - bYear || aSeason - bSeason
  })

  const cumulativeBest: Record<string, { credits: number; grade: string; points: number }> = {}
  const semesters: SemesterData[] = []
  let consecutiveProb = 0

  for (const sem of sortedSems) {
    const semCourses = semesterMap[sem]
    let semPts = 0
    let semCred = 0

    const displayRows: { course: string; credits: number; grade: string; status: string }[] = []

    for (const row of semCourses) {
      const course = row.Course_Code.toUpperCase()
      const grade = row.Grade.toUpperCase()
      const credits = parseFloat(row.Credits) || 0
      const pts = GRADE_POINTS[grade]

      const ex = cumulativeBest[course]
      let status = 'Counted'

      if (grade === 'W') status = 'Withdrawn'
      else if (grade === 'I') status = 'Incomplete'
      else if (grade === 'F') status = 'Failed'
      else if (grade === 'T') status = 'Waived'
      else if (ex) {
        if (ex.points >= 3.3) status = 'Illegal Retake'
        else status = 'Retake (Ignored)'
      }

      displayRows.push({ course, credits, grade, status })

      if (pts !== undefined && credits > 0 && grade !== 'T') {
        semPts += pts * credits
        semCred += credits
        if (!ex || pts > ex.points) {
          cumulativeBest[course] = { credits, grade, points: pts }
        }
      }
    }

    const rawTGPA = semCred > 0 ? semPts / semCred : 0
    const tgpa = Math.floor(rawTGPA * 100) / 100

    const totalPts = Object.values(cumulativeBest).reduce((sum, d) => sum + d.points * d.credits, 0)
    const totalCred = Object.values(cumulativeBest).reduce((sum, d) => sum + d.credits, 0)
    const rawCGPA = totalCred > 0 ? totalPts / totalCred : 0
    const cgpa = Math.floor(rawCGPA * 100) / 100

    if (totalCred > 0 && cgpa < 2.0) consecutiveProb++
    else consecutiveProb = 0

    semesters.push({
      semester: sem,
      courses: displayRows,
      tgpa,
      cgpa,
      semCredits: semCred,
      status: cgpa < 2.0 ? 'probation' : 'normal'
    })
  }

  const finalPts = Object.values(cumulativeBest).reduce((sum, d) => sum + d.points * d.credits, 0)
  const finalCred = Object.values(cumulativeBest).reduce((sum, d) => sum + d.credits, 0)
  const finalCGPA = finalCred > 0 ? Math.floor((finalPts / finalCred) * 100) / 100 : 0

  return {
    cgpa: finalCGPA,
    gpaCredits: finalCred,
    semesters,
    standing: consecutiveProb > 0 ? 'PROBATION' : 'NORMAL',
    consecutiveProbation: consecutiveProb
  }
}

function runLevel3(courses: CourseRow[], program: string) {
  const l1 = runLevel1(courses)
  const l2 = runLevel2(courses)
  
  const requirements: Record<string, { total: number; minCGPA: number; ged: string[]; math: string[]; core: string[]; science: string[]; business: string[] }> = {
    CSE: { total: 130, minCGPA: 2.0, ged: ['ENG102', 'ENG103', 'HIS103', 'PHI101', 'BEN205', 'POL101', 'ECO101', 'SOC101', 'ENV203'], math: ['MAT116', 'MAT120', 'MAT125', 'MAT130', 'MAT250', 'MAT350', 'MAT361'], core: ['CSE115', 'CSE115L', 'CSE173', 'CSE215', 'CSE215L', 'CSE225', 'CSE225L', 'CSE231', 'CSE231L', 'CSE311', 'CSE311L', 'CSE323', 'CSE323L', 'CSE327', 'CSE327L', 'CSE331', 'CSE331L', 'CSE332', 'CSE332L', 'CSE373', 'CSE425', 'CSE498R', 'CSE499'], science: ['PHY107', 'PHY107L', 'PHY108', 'PHY108L', 'CHE101', 'CHE101L'], business: [] },
    BBA: { total: 120, minCGPA: 2.0, ged: ['ENG102', 'ENG103', 'HIS103', 'PHI101', 'BEN205', 'ENV203', 'PSY101'], math: [], core: ['ACT201', 'ACT202', 'BUS172', 'ECO101', 'ECO104', 'FIN254', 'MGT210', 'MGT314', 'MGT368', 'MKT202', 'MIS205', 'LAW200', 'BUS101', 'BUS112', 'BUS134', 'BUS251', 'BUS401', 'BUS498', 'MGT321', 'MGT489', 'QM212'], science: [], business: [] },
    ETE: { total: 130, minCGPA: 2.0, ged: ['ENG102', 'ENG103', 'ENG111', 'HIS103', 'PHI101', 'POL101', 'SOC101', 'ENV203'], math: ['MAT116', 'MAT120', 'MAT125', 'MAT130', 'MAT350', 'MAT361'], core: ['ETE131', 'ETE131L', 'ETE132', 'ETE132L', 'ETE211', 'ETE211L', 'ETE212', 'ETE212L', 'ETE221', 'ETE283', 'ETE311', 'ETE311L', 'ETE331', 'ETE331L', 'ETE361', 'ETE381', 'ETE423', 'ETE424', 'ETE481', 'ETE499A', 'ETE499B'], science: ['PHY107', 'PHY107L', 'PHY108', 'PHY108L', 'CHE101', 'CHE101L'], business: [] },
    ENV: { total: 130, minCGPA: 2.0, ged: ['ENG103', 'ENG105', 'HIS103', 'PHI101'], math: ['MAT120', 'ENV172', 'ENV173'], core: ['ENV102', 'ENV107', 'ENV203', 'ENV205', 'ENV207', 'ENV208', 'ENV209', 'ENV214', 'ENV215', 'ENV260', 'ENV307', 'ENV315', 'ENV316', 'ENV373', 'ENV375', 'ENV405', 'ENV408', 'ENV409', 'ENV410', 'ENV414', 'ENV455', 'ENV498', 'ENV499'], science: ['CHE101', 'CHE101L', 'BIO103', 'BIO103L'], business: [] },
    ENG: { total: 123, minCGPA: 2.0, ged: ['HIS103', 'PHI101', 'SOC101', 'ENV203', 'POL101'], math: ['MIS105'], core: ['ENG109', 'ENG110', 'ENG111', 'ENG115', 'ENG210', 'ENG220', 'ENG230', 'ENG260', 'ENG311', 'ENG312', 'ENG321', 'ENG322', 'ENG331', 'ENG401', 'ENG402', 'ENG499'], science: ['SCI101'], business: [] },
    ECO: { total: 120, minCGPA: 2.0, ged: ['ENG103', 'ENG105', 'BEN205', 'HIS103', 'PHI101', 'POL101'], math: ['MAT125', 'ECO172', 'ECO173'], core: ['ECO101', 'ECO104', 'ECO201', 'ECO204', 'ECO317', 'ECO328', 'ECO349', 'ECO354', 'ECO372', 'ECO414', 'ECO490'], science: ['MIS107'], business: [] },
  }

  const req = requirements[program] || requirements.CSE
  const passedCourses = new Set<string>()
  const invalidElectives: string[] = []
  const allKnown = new Set([...req.ged, ...req.math, ...req.core, ...req.science, ...req.business])
  
  for (const row of courses) {
    const course = row.Course_Code.toUpperCase()
    const grade = row.Grade.toUpperCase()
    const isPassing = !['F', 'W', 'I', 'X'].includes(grade)
    
    if (isPassing || grade === 'T') {
      if (!allKnown.has(course)) {
        invalidElectives.push(course)
      }
      passedCourses.add(course)
    }
  }

  const missing: Record<string, string[]> = {
    GED: req.ged.filter(c => !passedCourses.has(c)),
    Math: req.math.filter(c => !passedCourses.has(c)),
    Core: req.core.filter(c => !passedCourses.has(c)),
    Science: req.science.filter(c => !passedCourses.has(c)),
    Business: req.business.filter(c => !passedCourses.has(c)),
  }

  const hasMissing = Object.values(missing).some(m => m.length > 0)
  const cgpaOk = l2.cgpa >= req.minCGPA
  const creditsOk = l1.totalCredits >= req.total
  const eligible = cgpaOk && creditsOk && !hasMissing && invalidElectives.length === 0

  return {
    eligible,
    totalEarned: l1.totalCredits,
    cgpa: l2.cgpa,
    totalRequired: req.total,
    minCGPA: req.minCGPA,
    missing,
    advisories: [],
    invalidElectives
  }
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    'Counted': 'status-success',
    'Failed': 'status-danger',
    'Withdrawn': 'status-warning',
    'Incomplete': 'status-warning',
    'Illegal Retake': 'status-danger',
    'Retake (Ignored)': 'status-info',
    'Waived': 'status-info',
  }
  
  const icons: Record<string, string> = {
    'Counted': '✓',
    'Failed': '✗',
    'Withdrawn': '~',
    'Incomplete': '?',
    'Illegal Retake': '⚠',
    'Retake (Ignored)': '↩',
    'Waived': '⊘',
  }
  
  return (
    <span className={`status-badge ${colors[status] || 'status-info'}`}>
      {icons[status] || '•'} {status}
    </span>
  )
}

function Level1Report({ result }: { result: AuditResult['level1'] }) {
  return (
    <div className="card animate-in">
      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px', color: 'var(--accent-2)' }}>
        L1 Credit Tally Report
      </h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: '30%' }}>Course</th>
              <th style={{ width: '15%', textAlign: 'right' }}>Credits</th>
              <th style={{ width: '15%', textAlign: 'center' }}>Grade</th>
              <th style={{ width: '40%' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, i) => (
              <tr key={i}>
                <td style={{ fontFamily: 'monospace' }}>{row.course}</td>
                <td style={{ textAlign: 'right' }}>{row.credits}</td>
                <td style={{ textAlign: 'center', fontWeight: 600 }}>{row.grade}</td>
                <td><StatusBadge status={row.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: '16px', padding: '16px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600 }}>Total Valid Earned Credits</span>
        <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--success)' }}>{result.totalCredits}</span>
      </div>
    </div>
  )
}

function Level2Report({ result }: { result: AuditResult['level2'] }) {
  return (
    <div className="card animate-in">
      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px', color: 'var(--accent-2)' }}>
        L2 Semester-by-Semester CGPA Report
      </h3>
      
      <div style={{ display: 'grid', gap: '20px' }}>
        {result.semesters.map((sem, idx) => (
          <div key={idx} className="semester-card">
            <div className="semester-header">
              <span style={{ fontWeight: 700 }}>{sem.semester}</span>
              <div style={{ display: 'flex', gap: '20px', fontSize: '0.85rem' }}>
                <span>Credits: <strong>{sem.semCredits}</strong></span>
                <span>TGPA: <strong style={{ color: sem.tgpa >= 2 ? 'var(--success)' : 'var(--danger)' }}>{sem.tgpa.toFixed(2)}</strong></span>
                <span>CGPA: <strong style={{ color: sem.cgpa >= 2 ? 'var(--success)' : 'var(--danger)' }}>{sem.cgpa.toFixed(2)}</strong></span>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Course</th>
                    <th style={{ textAlign: 'right' }}>Credits</th>
                    <th style={{ textAlign: 'center' }}>Grade</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sem.courses.map((course, ci) => (
                    <tr key={ci}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{course.course}</td>
                      <td style={{ textAlign: 'right' }}>{course.credits}</td>
                      <td style={{ textAlign: 'center', fontWeight: 600 }}>{course.grade}</td>
                      <td><StatusBadge status={course.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {sem.status === 'probation' && (
              <div style={{ padding: '8px 16px', background: 'rgba(244,63,94,0.1)', color: 'var(--danger)', fontSize: '0.85rem', borderTop: '1px solid var(--border)' }}>
                ⚠ ACADEMIC PROBATION (below 2.00)
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: '20px', padding: '20px', background: 'var(--surface-2)', borderRadius: 'var(--radius)', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', textAlign: 'center' }}>
        <div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent)' }}>{result.cgpa.toFixed(2)}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Final CGPA</div>
        </div>
        <div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent)' }}>{result.gpaCredits}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>GPA Credits</div>
        </div>
        <div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: result.standing === 'NORMAL' ? 'var(--success)' : 'var(--danger)' }}>{result.standing}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            {result.consecutiveProbation > 0 ? `(${result.consecutiveProbation} semesters)` : ''}
          </div>
        </div>
      </div>
    </div>
  )
}

function Level3Report({ result, program }: { result: AuditResult['level3']; program: string }) {
  return (
    <div className="card animate-in">
      <div style={{ 
        padding: '24px', 
        borderRadius: 'var(--radius)', 
        marginBottom: '20px',
        background: result.eligible ? 'rgba(34,197,94,0.1)' : 'rgba(244,63,94,0.1)',
        border: `2px solid ${result.eligible ? 'var(--success)' : 'var(--danger)'}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h3 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
            {result.eligible ? '✓ ELIGIBLE FOR GRADUATION' : '✗ NOT ELIGIBLE FOR GRADUATION'}
          </h3>
          <p style={{ color: 'var(--text-muted)', marginTop: '4px' }}>{program} Program</p>
        </div>
        <div style={{ fontSize: '2rem', fontWeight: 800, color: result.eligible ? 'var(--success)' : 'var(--danger)' }}>
          {result.eligible ? 'PASS' : 'FAIL'}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
        <div style={{ padding: '16px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Credits Earned</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '2rem', fontWeight: 800, color: result.totalEarned >= result.totalRequired ? 'var(--success)' : 'var(--danger)' }}>
              {result.totalEarned}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>/ {result.totalRequired} required</span>
          </div>
        </div>
        <div style={{ padding: '16px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>CGPA</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '2rem', fontWeight: 800, color: result.cgpa >= result.minCGPA ? 'var(--success)' : 'var(--danger)' }}>
              {result.cgpa.toFixed(2)}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>/ {result.minCGPA.toFixed(2)} minimum</span>
          </div>
        </div>
      </div>

      {!result.eligible && (
        <div style={{ padding: '16px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
          <h4 style={{ fontWeight: 700, color: 'var(--danger)', marginBottom: '16px' }}>⚠ Deficiency Report</h4>
          
          {result.cgpa < result.minCGPA && (
            <div style={{ marginBottom: '12px', padding: '12px', background: 'rgba(244,63,94,0.1)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--danger)' }}>
              <strong>Probation:</strong> CGPA {result.cgpa.toFixed(2)} is below the required minimum of {result.minCGPA.toFixed(2)}
            </div>
          )}
          
          {result.totalEarned < result.totalRequired && (
            <div style={{ marginBottom: '12px', padding: '12px', background: 'rgba(251,191,36,0.1)', borderRadius: 'var(--radius-sm)', border: '1px solid #fbbf24' }}>
              <strong>Credits:</strong> Need {result.totalRequired - result.totalEarned} more credits to reach {result.totalRequired}
            </div>
          )}

          {Object.entries(result.missing).map(([category, courses]) => {
            if (courses.length === 0) return null
            const catNames: Record<string, string> = { GED: 'General Education', Math: 'Core Mathematics', Core: 'Major Core', Science: 'Core Science', Business: 'Core Business' }
            return (
              <div key={category} style={{ marginBottom: '16px' }}>
                <h5 style={{ fontWeight: 600, color: 'var(--danger)', marginBottom: '8px' }}>
                  Missing {catNames[category]} ({courses.length} course{courses.length > 1 ? 's' : ''})
                </h5>
                <ul style={{ paddingLeft: '20px', fontSize: '0.9rem' }}>
                  {courses.map((course, i) => (
                    <li key={i} style={{ fontFamily: 'monospace', marginBottom: '4px' }}>{course}</li>
                  ))}
                </ul>
              </div>
            )
          })}

          {result.invalidElectives.length > 0 && (
            <div style={{ padding: '12px', background: 'rgba(251,191,36,0.1)', borderRadius: 'var(--radius-sm)', border: '1px solid #fbbf24' }}>
              <strong>Invalid Electives (credits excluded):</strong>
              <ul style={{ paddingLeft: '20px', fontSize: '0.9rem', marginTop: '8px' }}>
                {result.invalidElectives.map((course, i) => (
                  <li key={i} style={{ fontFamily: 'monospace' }}>{course}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {result.eligible && (
        <div style={{ padding: '16px', background: 'rgba(34,197,94,0.1)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--success)', textAlign: 'center', color: 'var(--success)', fontWeight: 600 }}>
          All graduation requirements have been met!
        </div>
      )}
    </div>
  )
}

export default function AuditPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [program, setProgram] = useState('CSE')
  const [csvText, setCsvText] = useState('')
  const [result, setResult] = useState<AuditResult | null>(null)
  const [activeTab, setActiveTab] = useState<'full' | 'l1' | 'l2' | 'l3'>('full')
  const [error, setError] = useState<string | null>(null)

  function handleFile(file: File) {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      setCsvText(text)
      setError(null)
    }
    reader.onerror = () => setError('Failed to read file')
    reader.readAsText(file)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  function runAudit() {
    if (!csvText.trim()) {
      setError('Please paste CSV data or upload a file')
      return
    }

    try {
      const courses = parseCSV(csvText)
      if (courses.length === 0) {
        setError('No valid course data found in CSV')
        return
      }

      const l1 = runLevel1(courses)
      const l2 = runLevel2(courses)
      const l3 = runLevel3(courses, program)

      setResult({
        level1: { totalCredits: l1.totalCredits, rows: l1.rows },
        level2: { cgpa: l2.cgpa, gpaCredits: l2.gpaCredits, semesters: l2.semesters, standing: l2.standing, consecutiveProbation: l2.consecutiveProbation },
        level3: l3
      })
      setError(null)
    } catch (err) {
      setError(`Error parsing CSV: ${err}`)
    }
  }

  const programName = PROGRAMS.find(p => p.code === program)?.name || program

  return (
    <>
      <Nav />
      <div className="container" style={{ paddingTop: '40px', paddingBottom: '40px' }}>
        <div className="page-header">
          <h1>NSU Transcript Audit</h1>
          <p>Run Level 1, 2, and 3 audits on student transcripts</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', alignItems: 'start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="card">
              <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>1. Select Program</h2>
              <select
                value={program}
                onChange={(e) => setProgram(e.target.value)}
                style={{ width: '100%' }}
              >
                {PROGRAMS.map(p => (
                  <option key={p.code} value={p.code}>{p.name} ({p.code})</option>
                ))}
              </select>
            </div>

            <div className="card">
              <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>2. Upload Transcript CSV</h2>
              <div
                className="upload-zone"
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
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
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
              />
              {csvText && (
                <p style={{ marginTop: '8px', fontSize: '0.85rem', color: 'var(--success)' }}>
                  ✓ CSV data loaded ({parseCSV(csvText).length} courses)
                </p>
              )}
            </div>

            <div className="card">
              <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>3. Paste CSV Data</h2>
              <textarea
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                placeholder={"Course_Code,Course_Name,Credits,Grade,Semester\nCSE115,Programming Language I,3,A,Spring2019\n..."}
                style={{ 
                  width: '100%', 
                  height: '160px', 
                  padding: '12px', 
                  border: '1px solid var(--border)', 
                  borderRadius: 'var(--radius-sm)', 
                  background: 'var(--surface-2)', 
                  color: 'var(--text)', 
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  resize: 'vertical'
                }}
              />
              <p style={{ marginTop: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Format: Course_Code,Course_Name,Credits,Grade,Semester (one per line)
              </p>
            </div>

            <button
              onClick={runAudit}
              className="btn btn-primary"
              style={{ width: '100%', padding: '16px', fontSize: '1rem' }}
            >
              Run Full Audit
            </button>

            {error && (
              <div style={{ padding: '12px', background: 'rgba(244,63,94,0.1)', border: '1px solid var(--danger)', borderRadius: 'var(--radius-sm)', color: 'var(--danger)' }}>
                {error}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {result && (
              <>
                <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  {(['full', 'l1', 'l2', 'l3'] as const).map(tab => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      style={{ 
                        padding: '8px 16px', 
                        fontWeight: 600, 
                        border: 'none', 
                        background: 'none', 
                        cursor: 'pointer',
                        borderBottom: `2px solid ${activeTab === tab ? 'var(--accent)' : 'transparent'}`,
                        color: activeTab === tab ? 'var(--accent)' : 'var(--text-muted)'
                      }}
                    >
                      {tab === 'full' ? 'Full Report' : `Level ${tab.slice(1)}`}
                    </button>
                  ))}
                </div>

                {activeTab === 'full' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <Level1Report result={result.level1} />
                    <Level2Report result={result.level2} />
                    <Level3Report result={result.level3} program={programName} />
                  </div>
                )}

                {activeTab === 'l1' && <Level1Report result={result.level1} />}
                {activeTab === 'l2' && <Level2Report result={result.level2} />}
                {activeTab === 'l3' && <Level3Report result={result.level3} program={programName} />}
              </>
            )}

            {!result && (
              <div style={{ padding: '60px', background: 'var(--surface-2)', borderRadius: 'var(--radius)', textAlign: 'center', color: 'var(--text-muted)' }}>
                Upload a transcript or paste CSV data to see audit results
              </div>
            )}
          </div>
        </div>
      </div>
      
      <style>{`
        .semester-card {
          border: 1px solid var(--border);
          border-radius: var(--radius);
          overflow: hidden;
        }
        .semester-header {
          padding: 12px 16px;
          background: var(--surface-2);
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-bottom: 1px solid var(--border);
        }
        .status-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 100px;
          font-size: 0.75rem;
          font-weight: 600;
        }
        .status-success { background: rgba(34,197,94,0.15); color: var(--success); }
        .status-danger { background: rgba(244,63,94,0.15); color: var(--danger); }
        .status-warning { background: rgba(251,191,36,0.15); color: #fbbf24; }
        .status-info { background: rgba(99,102,241,0.15); color: var(--accent); }
      `}</style>
      <Footer />
    </>
  )
}
