'use client'

import { useState, useMemo } from 'react'

interface AuditScan {
    audit_result?: {
        l1?: { total_credits?: number }
        l2?: { cgpa?: number }
        l3?: { graduation_eligible?: boolean; deficiencies?: string[] }
        graduation_status?: string
    }
    program?: string
    graduation_status?: string
    total_credits?: number
    cgpa?: number
    created_at?: string
    level1?: { totalCredits: number; rows: { course: string; credits: number; grade: string; status: string }[] }
    level2?: { cgpa: number; gpaCredits: number; standing: string }
    level3?: { eligible: boolean; totalEarned: number; cgpa: number; totalRequired: number; minCGPA: number; missing: Record<string, string[]>; advisories: string[] }
}

interface ParsedCourse {
    course: string
    courseName: string
    credits: number
    grade: string
    semester: string
    gradePoints: number
}

const GRADE_COLORS: Record<string, string> = {
    'A': 'var(--success)',
    'A-': 'var(--success)',
    'B+': 'var(--accent)',
    'B': 'var(--accent)',
    'B-': 'var(--accent)',
    'C+': '#fbbf24',
    'C': '#fbbf24',
    'C-': '#fbbf24',
    'D+': 'var(--danger)',
    'D': 'var(--danger)',
    'F': 'var(--danger)',
    'W': 'var(--text-muted)',
    'T': 'var(--accent)',
}

const GRADE_POINTS: Record<string, number> = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}

function parseCSV(csvText: string): ParsedCourse[] {
    const lines = csvText.trim().split('\n')
    const courses: ParsedCourse[] = []
    
    for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.toLowerCase().includes('course_code')) continue
        
        const parts = trimmed.split(',').map(p => p.trim())
        if (parts.length >= 5) {
            const grade = parts[3]?.toUpperCase() || ''
            const pts = GRADE_POINTS[grade] ?? 0
            courses.push({
                course: parts[0] || '',
                courseName: parts[1] || '',
                credits: parseFloat(parts[2]) || 3,
                grade: grade,
                semester: parts[4] || 'Unknown',
                gradePoints: pts
            })
        }
    }
    return courses
}

function semesterSortKey(sem: string): [number, number] {
    const parts = sem.trim().split(/\s+/)
    const seasonOrder: Record<string, number> = { Spring: 0, Summer: 1, Fall: 2 }
    if (parts.length === 2) {
        const season = parts[0]
        const year = parseInt(parts[1])
        if (!isNaN(year) && season in seasonOrder) {
            return [year, seasonOrder[season]]
        }
    }
    return [9999, 99]
}

function SemesterTable({ courses, semester }: { courses: ParsedCourse[]; semester: string }) {
    const semCreds = courses.reduce((sum, c) => sum + c.credits, 0)
    const semPts = courses.reduce((sum, c) => sum + (c.gradePoints * c.credits), 0)
    const semGPA = semCreds > 0 ? semPts / semCreds : 0

    return (
        <div className="semester-block">
            <div className="semester-header">
                <span className="semester-title">{semester}</span>
                <div className="semester-stats">
                    <span>{courses.length} courses</span>
                    <span>{semCreds} credits</span>
                    <span className="sem-gpa">TGPA: {semGPA.toFixed(2)}</span>
                </div>
            </div>
            <table className="semester-table">
                <thead>
                    <tr>
                        <th>Course</th>
                        <th>Name</th>
                        <th>Cr</th>
                        <th>Grade</th>
                        <th>Pts</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {courses.map((c, i) => (
                        <tr key={i}>
                            <td className="mono">{c.course}</td>
                            <td className="course-name">{c.courseName}</td>
                            <td className="num">{c.credits}</td>
                            <td className="grade" style={{ color: GRADE_COLORS[c.grade] || 'var(--text)' }}>
                                {c.grade}
                            </td>
                            <td className="num">{c.gradePoints.toFixed(1)}</td>
                            <td>
                                <StatusBadge status={c.grade === 'W' ? 'Withdrawn' : c.grade === 'T' ? 'Waived' : 'Counted'} />
                            </td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr>
                        <td colSpan={2} className="subtotal-label">Semester Total</td>
                        <td className="num">{semCreds}</td>
                        <td colSpan={3} className="subtotal-gpa">TGPA: {semGPA.toFixed(2)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    )
}

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, { bg: string; color: string }> = {
        'Counted': { bg: 'rgba(34,197,94,0.15)', color: 'var(--success)' },
        'Withdrawn': { bg: 'rgba(251,191,36,0.15)', color: '#fbbf24' },
        'Waived': { bg: 'rgba(99,102,241,0.15)', color: 'var(--accent)' },
        'Ignored': { bg: 'rgba(100,116,139,0.15)', color: 'var(--text-muted)' },
    }
    const s = styles[status] || styles['Counted']
    return (
        <span style={{
            padding: '2px 8px', borderRadius: '100px', fontSize: '0.7rem', fontWeight: 600,
            background: s.bg, color: s.color
        }}>
            {status}
        </span>
    )
}

function SummaryCard({ scan, totalCourses, cgpa, earnedCreds, requiredCreds }: {
    scan: AuditScan
    totalCourses: number
    cgpa: number
    earnedCreds: number
    requiredCreds: number
}) {
    const status = scan.graduation_status || scan.audit_result?.graduation_status || 'PENDING'
    const isPass = status === 'PASS'

    return (
        <div className="summary-card">
            <div className="summary-main">
                <div className="verdict" style={{ borderColor: isPass ? 'var(--success)' : 'var(--danger)' }}>
                    <span className="verdict-icon">{isPass ? '✓' : '✗'}</span>
                    <span className="verdict-text">{isPass ? 'ELIGIBLE FOR GRADUATION' : 'NOT ELIGIBLE'}</span>
                </div>
            </div>
            <div className="summary-stats">
                <div className="stat">
                    <span className="stat-val" style={{ color: 'var(--accent)' }}>{totalCourses}</span>
                    <span className="stat-label">Courses</span>
                </div>
                <div className="stat">
                    <span className="stat-val" style={{ color: 'var(--success)' }}>{earnedCreds}</span>
                    <span className="stat-label">Credits</span>
                </div>
                <div className="stat">
                    <span className="stat-val" style={{ color: cgpa >= 2.0 ? 'var(--success)' : 'var(--danger)' }}>
                        {cgpa.toFixed(2)}
                    </span>
                    <span className="stat-label">CGPA</span>
                </div>
                <div className="stat">
                    <span className="stat-val">{requiredCreds}</span>
                    <span className="stat-label">Required</span>
                </div>
            </div>
            {!isPass && (
                <div className="summary-alert">
                    <span>Need {requiredCreds - earnedCreds} more credits</span>
                </div>
            )}
        </div>
    )
}

export default function AuditReport({ scan, csvText }: { scan: AuditScan; csvText?: string }) {
    const [activeTab, setActiveTab] = useState<'semesters' | 'summary' | 'json'>('semesters')
    const [copied, setCopied] = useState(false)

    const { semesters, totalCourses, cgpa, earnedCreds, requiredCreds } = useMemo(() => {
        const courses = csvText ? parseCSV(csvText) : []
        
        const semMap: Record<string, ParsedCourse[]> = {}
        for (const c of courses) {
            if (!semMap[c.semester]) semMap[c.semester] = []
            semMap[c.semester].push(c)
        }
        
        const sortedSems = Object.keys(semMap).sort((a, b) => {
            const [aY, aS] = semesterSortKey(a)
            const [bY, bS] = semesterSortKey(b)
            return aY - bY || aS - bS
        })
        
        const total = courses.length
        const earned = courses.filter(c => !['F', 'W', 'I', 'X'].includes(c.grade)).reduce((sum, c) => sum + c.credits, 0)
        
        let cumGPA = 0
        let cumCreds = 0
        for (const sem of sortedSems) {
            const semCourses = semMap[sem]
            const semCreds = semCourses.reduce((s, c) => s + c.credits, 0)
            const semPts = semCourses.reduce((s, c) => s + (c.gradePoints * c.credits), 0)
            cumGPA += semPts
            cumCreds += semCreds
        }
        const finalCGPA = cumCreds > 0 ? cumGPA / cumCreds : 0
        
        const req = scan.level3?.totalRequired || scan.level3?.totalEarned || 120
        
        return {
            semesters: sortedSems.map(sem => ({ name: sem, courses: semMap[sem] })),
            totalCourses: total,
            cgpa: finalCGPA,
            earnedCreds: earned,
            requiredCreds: req
        }
    }, [csvText, scan])

    const copyToClipboard = () => {
        navigator.clipboard.writeText(JSON.stringify(scan, null, 2))
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const downloadCSV = () => {
        if (!csvText) return
        const blob = new Blob([csvText], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `audit_${Date.now()}.csv`
        a.click()
        URL.revokeObjectURL(url)
    }

    const downloadJSON = () => {
        const blob = new Blob([JSON.stringify(scan, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `audit_${Date.now()}.json`
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <div className="audit-report card animate-in">
            <div className="report-header">
                <h2>Audit Report</h2>
                <div className="action-buttons">
                    <button onClick={copyToClipboard} className="action-btn">
                        {copied ? '✓ Copied' : '📋 Copy JSON'}
                    </button>
                    {csvText && (
                        <button onClick={downloadCSV} className="action-btn">
                            📥 Download CSV
                        </button>
                    )}
                    <button onClick={downloadJSON} className="action-btn">
                        📥 Download JSON
                    </button>
                </div>
            </div>

            <SummaryCard
                scan={scan}
                totalCourses={totalCourses}
                cgpa={cgpa}
                earnedCreds={earnedCreds}
                requiredCreds={requiredCreds}
            />

            <div className="tab-bar">
                <button className={`tab ${activeTab === 'semesters' ? 'active' : ''}`} onClick={() => setActiveTab('semesters')}>
                    📅 By Semester
                </button>
                <button className={`tab ${activeTab === 'summary' ? 'active' : ''}`} onClick={() => setActiveTab('summary')}>
                    📊 Summary
                </button>
                <button className={`tab ${activeTab === 'json' ? 'active' : ''}`} onClick={() => setActiveTab('json')}>
                    { } Raw JSON
                </button>
            </div>

            {activeTab === 'semesters' && (
                <div className="semesters-list">
                    {semesters.length > 0 ? (
                        semesters.map((sem, i) => (
                            <SemesterTable key={i} semester={sem.name} courses={sem.courses} />
                        ))
                    ) : (
                        <div className="no-data">No semester data available. Upload a CSV with semester information.</div>
                    )}
                </div>
            )}

            {activeTab === 'summary' && (
                <div className="summary-view">
                    <div className="summary-row">
                        <span>Total Courses</span>
                        <span className="mono">{totalCourses}</span>
                    </div>
                    <div className="summary-row">
                        <span>Total Credits Earned</span>
                        <span className="mono">{earnedCreds}</span>
                    </div>
                    <div className="summary-row">
                        <span>CGPA</span>
                        <span className="mono" style={{ color: cgpa >= 2.0 ? 'var(--success)' : 'var(--danger)' }}>
                            {cgpa.toFixed(2)}
                        </span>
                    </div>
                    <div className="summary-row">
                        <span>Credits Required</span>
                        <span className="mono">{requiredCreds}</span>
                    </div>
                    <div className="summary-row">
                        <span>Credits Remaining</span>
                        <span className="mono" style={{ color: earnedCreds >= requiredCreds ? 'var(--success)' : 'var(--danger)' }}>
                            {Math.max(0, requiredCreds - earnedCreds)}
                        </span>
                    </div>
                    <div className="summary-row">
                        <span>Graduation Status</span>
                        <span className={`status-badge ${scan.graduation_status === 'PASS' ? 'pass' : 'fail'}`}>
                            {scan.graduation_status || 'PENDING'}
                        </span>
                    </div>
                </div>
            )}

            {activeTab === 'json' && (
                <pre className="json-view">{JSON.stringify(scan, null, 2)}</pre>
            )}

            <style>{`
                .audit-report { padding: 24px; }
                .report-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .report-header h2 { margin: 0; font-size: 1.3rem; }
                .action-buttons { display: flex; gap: 8px; }
                .action-btn { padding: 6px 12px; border: 1px solid var(--border); background: var(--surface-2); border-radius: var(--radius-sm); cursor: pointer; font-size: 0.8rem; color: var(--text); }
                .action-btn:hover { background: var(--surface); }
                
                .summary-card { background: var(--surface-2); border-radius: var(--radius); padding: 20px; margin-bottom: 20px; border: 1px solid var(--border); }
                .summary-main { margin-bottom: 16px; }
                .verdict { display: inline-flex; align-items: center; gap: 12px; padding: 12px 20px; border: 2px solid; border-radius: var(--radius-sm); }
                .verdict-icon { font-size: 1.5rem; font-weight: 800; }
                .verdict-text { font-size: 1.1rem; font-weight: 700; }
                .summary-stats { display: flex; gap: 32px; }
                .stat { text-align: center; }
                .stat-val { font-size: 2rem; font-weight: 800; display: block; }
                .stat-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }
                .summary-alert { margin-top: 12px; padding: 8px 16px; background: rgba(244,63,94,0.1); border-radius: var(--radius-sm); color: var(--danger); font-weight: 600; text-align: center; }
                
                .tab-bar { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
                .tab { padding: 10px 16px; background: none; border: none; cursor: pointer; font-size: 0.9rem; color: var(--text-muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
                .tab:hover { color: var(--text); }
                .tab.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
                
                .semesters-list { display: flex; flex-direction: column; gap: 20px; }
                .semester-block { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
                .semester-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--surface-2); border-bottom: 1px solid var(--border); }
                .semester-title { font-weight: 700; color: var(--accent); }
                .semester-stats { display: flex; gap: 16px; font-size: 0.85rem; color: var(--text-muted); }
                .sem-gpa { color: var(--accent); font-weight: 600; }
                
                .semester-table { width: 100%; border-collapse: collapse; }
                .semester-table th { padding: 8px 12px; text-align: left; font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); border-bottom: 1px solid var(--border); background: var(--surface); }
                .semester-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
                .semester-table tr:last-child td { border-bottom: none; }
                .semester-table .mono { font-family: monospace; font-weight: 600; }
                .semester-table .num { text-align: center; width: 50px; }
                .semester-table .grade { font-weight: 700; text-align: center; width: 60px; }
                .semester-table .course-name { color: var(--text-muted); font-size: 0.85rem; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
                .semester-table tfoot td { background: var(--surface-2); font-weight: 600; font-size: 0.85rem; }
                .subtotal-label { color: var(--text-muted); }
                .subtotal-gpa { text-align: right; color: var(--accent); }
                
                .summary-view { display: flex; flex-direction: column; gap: 12px; }
                .summary-row { display: flex; justify-content: space-between; padding: 12px 16px; background: var(--surface-2); border-radius: var(--radius-sm); }
                .summary-row .mono { font-family: monospace; font-weight: 700; }
                .status-badge { padding: 4px 12px; border-radius: 100px; font-weight: 600; font-size: 0.85rem; }
                .status-badge.pass { background: rgba(34,197,94,0.15); color: var(--success); }
                .status-badge.fail { background: rgba(244,63,94,0.15); color: var(--danger); }
                
                .json-view { background: var(--surface-2); padding: 16px; border-radius: var(--radius-sm); font-family: monospace; font-size: 0.75rem; overflow: auto; max-height: 400px; white-space: pre-wrap; }
                .no-data { text-align: center; padding: 40px; color: var(--text-muted); }
            `}</style>
        </div>
    )
}
