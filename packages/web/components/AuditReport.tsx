'use client'

import { useState, useMemo } from 'react'

interface AuditScan {
    program?: string
    graduation_status?: string
    total_credits?: number
    cgpa?: number
    level1?: { totalCredits: number; rows: { course: string; credits: number; grade: string; status: string }[] }
    level2?: { cgpa: number; gpaCredits: number; standing: string }
    level3?: { eligible: boolean; totalEarned: number; cgpa: number; totalRequired: number; minCGPA: number; missing: Record<string, string[]>; advisories: string[] }
}

interface CourseRow {
    course: string
    courseName: string
    credits: number
    grade: string
    semester: string
}

interface DisplayCourse extends CourseRow {
    status: string
    isRetake: boolean
    semesterCredits: number
    semesterTGPA: number
    cumulativeCGPA: number
    isProbation: boolean
}

const GRADE_POINTS: Record<string, number> = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}

function isPassing(grade: string): boolean {
    return !['F', 'W', 'I', 'X'].includes(grade.toUpperCase())
}


function parseCSV(csvText: string): CourseRow[] {
    const lines = csvText.trim().split('\n')
    const courses: CourseRow[] = []
    
    for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.toLowerCase().includes('course_code')) continue
        
        // Handle quoted values
        const parts: string[] = []
        let current = ''
        let inQuotes = false
        
        for (const char of line) {
            if (char === '"') inQuotes = !inQuotes
            else if (char === ',' && !inQuotes) {
                parts.push(current.trim())
                current = ''
            } else current += char
        }
        parts.push(current.trim())
        
        if (parts.length >= 5) {
            courses.push({
                course: parts[0].replace(/"/g, '').toUpperCase(),
                courseName: parts[1].replace(/"/g, ''),
                credits: parseFloat(parts[2]) || 3,
                grade: parts[3].replace(/"/g, '').toUpperCase(),
                semester: parts[4].replace(/"/g, '') || 'Unknown'
            })
        }
    }
    return courses
}

function semesterSortKey(sem: string): [number, number] {
    const match = sem.match(/(\d{4})/)
    const year = match ? parseInt(match[1]) : 9999
    const seasonOrder: Record<string, number> = { Spring: 0, Summer: 1, Fall: 2 }
    for (const [season, order] of Object.entries(seasonOrder)) {
        if (sem.toLowerCase().includes(season.toLowerCase())) return [year, order]
    }
    return [year, 99]
}

function getStatusIcon(status: string): string {
    const icons: Record<string, string> = {
        'Counted': '✓',
        'Retake (Ignored)': '↩',
        'Illegal Retake': '⚠',
        'Failed': '✗',
        'Withdrawn': '~',
        'Incomplete': '?',
        'Waived': '⊘'
    }
    return icons[status] || '·'
}

function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
        'Counted': '#22c55e',
        'Retake (Ignored)': '#eab308',
        'Illegal Retake': '#ef4444',
        'Failed': '#ef4444',
        'Withdrawn': '#eab308',
        'Incomplete': '#eab308',
        'Waived': '#8b5cf6'
    }
    return colors[status] || '#9ca3af'
}

function getGradeColor(grade: string): string {
    if (grade === 'A' || grade === 'A-') return '#22c55e'
    if (grade === 'B+' || grade === 'B' || grade === 'B-') return '#3b82f6'
    if (grade === 'C+' || grade === 'C' || grade === 'C-') return '#eab308'
    if (grade === 'D+' || grade === 'D' || grade === 'F') return '#ef4444'
    return '#9ca3af'
}

export default function AuditReport({ scan, csvText }: { scan: AuditScan; csvText?: string }) {
    const [showJson, setShowJson] = useState(false)
    const [copied, setCopied] = useState(false)

    const { semesters, finalCGPA, totalCreds, status, semesterData } = useMemo(() => {
        if (!csvText) {
            return { semesters: [], finalCGPA: 0, totalCreds: 0, status: 'PENDING', semesterData: {} }
        }

        const courses = parseCSV(csvText)
        
        const semMap: Record<string, CourseRow[]> = {}
        for (const c of courses) {
            if (!semMap[c.semester]) semMap[c.semester] = []
            semMap[c.semester].push(c)
        }
        
        const sortedSems = Object.keys(semMap).sort((a, b) => {
            const [aY, aS] = semesterSortKey(a)
            const [bY, bS] = semesterSortKey(b)
            return aY - bY || aS - bS
        })
        
        const cumulativeBest: Record<string, { credits: number; grade: string; points: number }> = {}
        let consecutiveProb = 0
        
        const semData: Record<string, DisplayCourse[]> = {}
        const semMeta: Record<string, { tgpa: number; cgpa: number; creds: number; isProb: boolean }> = {}
        
        for (let i = 0; i < sortedSems.length; i++) {
            const sem = sortedSems[i]
            const semCourses = semMap[sem]
            const displayCourses: DisplayCourse[] = []
            
            let semPts = 0
            let semCreds = 0
            
            for (const c of semCourses) {
                const pts = GRADE_POINTS[c.grade] ?? null
                const isWaived = c.grade.toUpperCase() === 'T'
                const existing = cumulativeBest[c.course]
                
                let status = 'Counted'
                let isRetake = existing !== undefined
                
                if (isWaived) {
                    status = 'Waived'
                } else if (isRetake) {
                    if (existing.points >= 3.3) {
                        status = 'Illegal Retake'
                    } else {
                        status = 'Retake (Ignored)'
                    }
                } else if (!isPassing(c.grade)) {
                    status = c.grade.toUpperCase() === 'W' ? 'Withdrawn' : c.grade.toUpperCase() === 'I' ? 'Incomplete' : 'Failed'
                }
                
                if (pts !== null && c.credits > 0 && !isWaived) {
                    semPts += pts * c.credits
                    semCreds += c.credits
                }
                
                if (pts !== null && !isWaived) {
                    if (existing === undefined || pts > existing.points) {
                        cumulativeBest[c.course] = { credits: c.credits, grade: c.grade, points: pts }
                    }
                }
                
                displayCourses.push({
                    ...c,
                    status,
                    isRetake,
                    semesterCredits: 0,
                    semesterTGPA: 0,
                    cumulativeCGPA: 0,
                    isProbation: consecutiveProb > 0
                })
            }
            
            semData[sem] = displayCourses
            
            const tgpa = semCreds > 0 ? semPts / semCreds : 0
            
            let cgpaPts = 0
            let cgpaCreds = 0
            for (const entry of Object.values(cumulativeBest)) {
                if (entry.credits > 0) {
                    cgpaPts += entry.points * entry.credits
                    cgpaCreds += entry.credits
                }
            }
            const cgpa = cgpaCreds > 0 ? cgpaPts / cgpaCreds : 0
            
            if (cgpaCreds > 0 && cgpa < 2.0) {
                consecutiveProb++
            } else {
                consecutiveProb = 0
            }
            
            semMeta[sem] = { tgpa, cgpa, creds: semCreds, isProb: consecutiveProb > 0 }
            
            for (const dc of displayCourses) {
                dc.semesterCredits = semCreds
                dc.semesterTGPA = tgpa
                dc.cumulativeCGPA = cgpa
                dc.isProbation = consecutiveProb > 0
            }
        }
        
        let finalPts = 0
        let finalCreds = 0
        for (const entry of Object.values(cumulativeBest)) {
            if (entry.credits > 0) {
                finalPts += entry.points * entry.credits
                finalCreds += entry.credits
            }
        }
        const finalCGPA = finalCreds > 0 ? finalPts / finalCreds : 0
        
        return {
            semesters: sortedSems.map(sem => ({
                name: sem,
                courses: semData[sem],
                semCreds: semMeta[sem].creds,
                semTGPA: semMeta[sem].tgpa,
                hasRetakes: semData[sem].some(c => c.isRetake),
                hasProbation: semMeta[sem].isProb
            })),
            finalCGPA,
            totalCreds: finalCreds,
            status: scan.graduation_status || 'PENDING',
            semesterData: semData
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
        <div className="cli-audit">
            <div className="cli-header">
                <div className="cli-title">╔═══════════════════════════════════════════════════════════╗
║  SEMESTER-BY-SEMESTER CGPA REPORT                             ║
╚═══════════════════════════════════════════════════════════╝</div>
                <div className="cli-actions">
                    <button onClick={copyToClipboard}>{copied ? '✓' : '📋'}</button>
                    {csvText && <button onClick={downloadCSV}>📥</button>}
                    <button onClick={downloadJSON}>JSON</button>
                </div>
            </div>

            <div className="cli-verdict">
                <span className={`verdict-box ${status === 'PASS' ? 'pass' : 'fail'}`}>
                    {status === 'PASS' ? '✓ ELIGIBLE FOR GRADUATION' : '✗ NOT ELIGIBLE FOR GRADUATION'}
                </span>
            </div>

            <div className="cli-summary">
                <span>Final CGPA: <strong style={{ color: finalCGPA >= 2.0 ? '#22c55e' : '#ef4444' }}>{finalCGPA.toFixed(2)}</strong></span>
                <span>Total GPA Credits: <strong>{totalCreds}</strong></span>
            </div>

            <div className="cli-semesters">
                {semesters.map((sem, i) => {
                    const cgpa = sem.courses[0]?.cumulativeCGPA || 0
                    return (
                        <div key={i} className="cli-block">
                            <div className="cli-block-header">
                                <span className="cli-sem">┌─ {sem.name}</span>
                                <span className="cli-sep">───────────────────────────────────────────</span>
                                <span className="cli-stats">
                                    {sem.semCreds} cr | TGPA: {sem.semTGPA.toFixed(2)} | CGPA: {cgpa.toFixed(2)}
                                </span>
                            </div>
                            <div className="cli-table">
                                <div className="cli-row cli-header-row">
                                    <span>Course</span>
                                    <span>Cr</span>
                                    <span>Grade</span>
                                    <span>Status</span>
                                </div>
                                {sem.courses.map((c, j) => (
                                    <div key={j} className={`cli-row ${c.isRetake ? 'retake' : ''}`}>
                                        <span className="mono">{c.course}</span>
                                        <span>{c.credits}</span>
                                        <span style={{ color: getGradeColor(c.grade), fontWeight: 700 }}>{c.grade}</span>
                                        <span style={{ color: getStatusColor(c.status) }}>
                                            {getStatusIcon(c.status)} {c.status}
                                        </span>
                                    </div>
                                ))}
                            </div>
                            <div className="cli-block-footer">
                                <span>{sem.hasProbation ? '├─ ⚠ PROBATION' : '├─ ✓ Good Standing'}</span>
                            </div>
                        </div>
                    )
                })}
            </div>

            <div className="cli-final">
╔═══════════════════════════════════════════════════════════╗
║  FINAL SUMMARY                                          ║
╠═══════════════════════════════════════════════════════════╣
║  Final CGPA: <strong>{finalCGPA.toFixed(2)}</strong> | Credits: <strong>{totalCreds}</strong>
╚═══════════════════════════════════════════════════════════╝
            </div>

            <button className="toggle-json" onClick={() => setShowJson(!showJson)}>
                {showJson ? '▲ Hide JSON' : '▼ Show JSON'}
            </button>

            {showJson && <pre className="cli-json">{JSON.stringify(scan, null, 2)}</pre>}

            <style>{`
                .cli-audit {
                    font-family: 'Consolas', 'Monaco', monospace;
                    background: var(--surface);
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 16px;
                    margin: 16px 0;
                }
                .cli-header { display: flex; justify-content: space-between; margin-bottom: 16px; }
                .cli-title { color: var(--text-muted); font-size: 0.7rem; white-space: pre; }
                .cli-actions { display: flex; gap: 4px; }
                .cli-actions button { padding: 4px 8px; border: 1px solid var(--border); background: var(--surface-2); border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
                .cli-verdict { margin-bottom: 12px; }
                .verdict-box { display: inline-block; padding: 8px 16px; border: 2px solid; border-radius: 6px; font-weight: 700; font-size: 0.9rem; }
                .verdict-box.pass { border-color: #22c55e; color: #22c55e; background: rgba(34,197,94,0.1); }
                .verdict-box.fail { border-color: #ef4444; color: #ef4444; background: rgba(239,68,68,0.1); }
                .cli-summary { display: flex; gap: 16px; padding: 8px 12px; background: var(--surface-2); border-radius: 6px; margin-bottom: 16px; font-size: 0.85rem; }
                .cli-semesters { display: flex; flex-direction: column; gap: 8px; }
                .cli-block { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
                .cli-block-header { display: flex; padding: 6px 10px; background: var(--surface-2); font-size: 0.8rem; border-bottom: 1px solid var(--border); }
                .cli-sem { color: var(--accent); font-weight: 600; }
                .cli-sep { flex: 1; color: var(--border); overflow: hidden; font-size: 0.6rem; }
                .cli-stats { color: var(--text-muted); white-space: nowrap; }
                .cli-table { padding: 4px 10px; }
                .cli-row { display: grid; grid-template-columns: 90px 35px 50px 1fr; gap: 8px; padding: 3px 0; font-size: 0.8rem; align-items: center; }
                .cli-row.retake { opacity: 0.5; }
                .cli-header-row { color: var(--text-muted); font-size: 0.65rem; text-transform: uppercase; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
                .cli-block-footer { padding: 4px 10px; background: var(--surface-2); font-size: 0.7rem; color: var(--text-muted); }
                .cli-final { margin-top: 16px; color: var(--text-muted); font-size: 0.7rem; white-space: pre; line-height: 1.4; }
                .cli-json { margin-top: 12px; background: var(--surface-2); padding: 12px; border-radius: 6px; font-size: 0.7rem; overflow: auto; max-height: 300px; white-space: pre-wrap; }
                .toggle-json { margin-top: 12px; width: 100%; padding: 6px; border: 1px solid var(--border); background: var(--surface-2); border-radius: 4px; cursor: pointer; color: var(--text-muted); font-size: 0.75rem; font-family: inherit; }
                .mono { font-weight: 600; }
            `}</style>
        </div>
    )
}
