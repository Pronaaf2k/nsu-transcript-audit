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

interface ParsedCourse {
    course: string
    courseName: string
    credits: number
    grade: string
    semester: string
    gradePoints: number
    status?: string
    verified?: boolean
}

interface CourseEditorProps {
    initialCourses: ParsedCourse[]
    onSave: (courses: ParsedCourse[], csvText: string) => void
    onCancel: () => void
}

const GRADE_POINTS: Record<string, number> = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}

const SEMESTERS = ['Spring', 'Summer', 'Fall']
const YEARS = Array.from({ length: 15 }, (_, i) => 2007 + i)

function CourseEditor({ initialCourses, onSave, onCancel }: CourseEditorProps) {
    const [courses, setCourses] = useState<ParsedCourse[]>(
        initialCourses.map(c => ({ ...c, verified: true }))
    )
    const [editingIndex, setEditingIndex] = useState<number | null>(null)
    const [isAdding, setIsAdding] = useState(false)
    const [newCourse, setNewCourse] = useState({ course: '', courseName: '', credits: '3', grade: 'A', semester: 'Spring 2024' })

    const updateCourse = (index: number, field: keyof ParsedCourse, value: string | number | boolean) => {
        const updated = [...courses]
        updated[index] = { ...updated[index], [field]: value, verified: false }
        
        if (field === 'grade') {
            updated[index].gradePoints = GRADE_POINTS[value as string] ?? 0
        }
        
        setCourses(updated)
    }

    const addCourse = () => {
        if (!newCourse.course.trim()) return
        
        const pts = GRADE_POINTS[newCourse.grade] ?? 0
        setCourses([...courses, {
            course: newCourse.course.toUpperCase(),
            courseName: newCourse.courseName,
            credits: parseFloat(newCourse.credits) || 3,
            grade: newCourse.grade,
            semester: newCourse.semester,
            gradePoints: pts,
            status: 'Counted',
            verified: true
        }])
        
        setNewCourse({ course: '', courseName: '', credits: '3', grade: 'A', semester: 'Spring 2024' })
        setIsAdding(false)
    }

    const deleteCourse = (index: number) => {
        setCourses(courses.filter((_, i) => i !== index))
    }

    const handleSave = () => {
        const csvLines = ['Course_Code,Course_Name,Credits,Grade,Semester']
        courses.forEach(c => {
            csvLines.push(`${c.course},${c.courseName},${c.credits},${c.grade},${c.semester}`)
        })
        onSave(courses, csvLines.join('\n'))
    }

    const totalCreds = courses.filter(c => !['F', 'W', 'I', 'X'].includes(c.grade))
        .reduce((sum, c) => sum + c.credits, 0)
    
    const unverified = courses.filter(c => !c.verified).length

    return (
        <div className="course-editor">
            <div className="editor-header">
                <h3>📝 Review & Edit Courses</h3>
                <p className="editor-info">
                    {courses.length} courses | {totalCreds} credits
                    {unverified > 0 && <span className="unverified"> | {unverified} unverified</span>}
                </p>
            </div>

            <div className="editor-actions">
                <button className="btn btn-primary" onClick={handleSave}>
                    ✓ Save & Run Audit
                </button>
                <button className="btn btn-outline" onClick={onCancel}>
                    Cancel
                </button>
                <button className="btn btn-accent" onClick={() => setIsAdding(true)}>
                    + Add Course
                </button>
            </div>

            {isAdding && (
                <div className="add-course-form">
                    <h4>Add New Course</h4>
                    <div className="form-grid">
                        <div className="form-group">
                            <label>Course Code</label>
                            <input
                                type="text"
                                placeholder="CSE101"
                                value={newCourse.course}
                                onChange={e => setNewCourse({...newCourse, course: e.target.value})}
                                style={{ textTransform: 'uppercase' }}
                            />
                        </div>
                        <div className="form-group">
                            <label>Course Name</label>
                            <input
                                type="text"
                                placeholder="Introduction to Programming"
                                value={newCourse.courseName}
                                onChange={e => setNewCourse({...newCourse, courseName: e.target.value})}
                            />
                        </div>
                        <div className="form-group">
                            <label>Credits</label>
                            <input
                                type="number"
                                min="1"
                                max="6"
                                value={newCourse.credits}
                                onChange={e => setNewCourse({...newCourse, credits: e.target.value})}
                            />
                        </div>
                        <div className="form-group">
                            <label>Grade</label>
                            <select
                                value={newCourse.grade}
                                onChange={e => setNewCourse({...newCourse, grade: e.target.value})}
                            >
                                {Object.keys(GRADE_POINTS).map(g => (
                                    <option key={g} value={g}>{g}</option>
                                ))}
                                <option value="W">W (Withdrawn)</option>
                                <option value="T">T (Transfer)</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Semester</label>
                            <select
                                value={newCourse.semester}
                                onChange={e => setNewCourse({...newCourse, semester: e.target.value})}
                            >
                                {YEARS.map(year => 
                                    SEMESTERS.map(sem => (
                                        <option key={`${sem}${year}`} value={`${sem} ${year}`}>
                                            {sem} {year}
                                        </option>
                                    ))
                                )}
                            </select>
                        </div>
                    </div>
                    <div className="form-actions">
                        <button className="btn btn-primary" onClick={addCourse}>Add</button>
                        <button className="btn btn-outline" onClick={() => setIsAdding(false)}>Cancel</button>
                    </div>
                </div>
            )}

            <div className="courses-table">
                <div className="table-header">
                    <span>Course</span>
                    <span>Name</span>
                    <span>Cr</span>
                    <span>Grade</span>
                    <span>Semester</span>
                    <span>Status</span>
                    <span></span>
                </div>
                {courses.map((course, index) => (
                    <div key={index} className={`table-row ${!course.verified ? 'unverified' : ''}`}>
                        {editingIndex === index ? (
                            <>
                                <input
                                    type="text"
                                    value={course.course}
                                    onChange={e => updateCourse(index, 'course', e.target.value.toUpperCase())}
                                    className="edit-input"
                                />
                                <input
                                    type="text"
                                    value={course.courseName}
                                    onChange={e => updateCourse(index, 'courseName', e.target.value)}
                                    className="edit-input"
                                />
                                <input
                                    type="number"
                                    value={course.credits}
                                    onChange={e => updateCourse(index, 'credits', parseFloat(e.target.value) || 3)}
                                    className="edit-input small"
                                />
                                <select
                                    value={course.grade}
                                    onChange={e => updateCourse(index, 'grade', e.target.value)}
                                    className="edit-select"
                                >
                                    {Object.keys(GRADE_POINTS).map(g => (
                                        <option key={g} value={g}>{g}</option>
                                    ))}
                                    <option value="W">W</option>
                                </select>
                                <select
                                    value={course.semester}
                                    onChange={e => updateCourse(index, 'semester', e.target.value)}
                                    className="edit-select"
                                >
                                    {YEARS.map(year => 
                                        SEMESTERS.map(sem => (
                                            <option key={`${sem}${year}`} value={`${sem} ${year}`}>
                                                {sem} {year}
                                            </option>
                                        ))
                                    )}
                                </select>
                                <span className="status-badge">Editing</span>
                                <button className="btn-icon" onClick={() => setEditingIndex(null)}>✓</button>
                            </>
                        ) : (
                            <>
                                <span className="mono">{course.course}</span>
                                <span className="course-name">{course.courseName}</span>
                                <span>{course.credits}</span>
                                <span className={`grade grade-${course.grade}`}>{course.grade}</span>
                                <span>{course.semester}</span>
                                <span className={`status-badge ${course.verified ? 'verified' : 'unverified'}`}>
                                    {course.verified ? '✓' : '?'}
                                </span>
                                <div className="row-actions">
                                    <button className="btn-icon" onClick={() => setEditingIndex(index)}>✏️</button>
                                    <button className="btn-icon delete" onClick={() => deleteCourse(index)}>🗑️</button>
                                </div>
                            </>
                        )}
                    </div>
                ))}
            </div>

            <style>{`
                .course-editor {
                    background: var(--surface);
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                    padding: 20px;
                    margin: 16px 0;
                }
                .editor-header {
                    margin-bottom: 16px;
                }
                .editor-header h3 {
                    margin: 0 0 8px 0;
                    color: var(--text);
                }
                .editor-info {
                    color: var(--text-muted);
                    font-size: 0.9rem;
                    margin: 0;
                }
                .unverified {
                    color: #eab308;
                }
                .editor-actions {
                    display: flex;
                    gap: 12px;
                    margin-bottom: 20px;
                }
                .btn {
                    padding: 8px 16px;
                    border-radius: var(--radius-sm);
                    font-weight: 600;
                    cursor: pointer;
                    border: none;
                }
                .btn-primary {
                    background: var(--accent);
                    color: white;
                }
                .btn-outline {
                    background: transparent;
                    border: 1px solid var(--border);
                    color: var(--text);
                }
                .btn-accent {
                    background: var(--success);
                    color: white;
                }
                .add-course-form {
                    background: var(--surface-2);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-sm);
                    padding: 16px;
                    margin-bottom: 20px;
                }
                .add-course-form h4 {
                    margin: 0 0 12px 0;
                }
                .form-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 12px;
                    margin-bottom: 12px;
                }
                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
                .form-group label {
                    font-size: 0.8rem;
                    color: var(--text-muted);
                }
                .form-group input,
                .form-group select {
                    padding: 8px;
                    border: 1px solid var(--border);
                    border-radius: var(--radius-sm);
                    background: var(--surface);
                    color: var(--text);
                    font-size: 0.9rem;
                }
                .form-actions {
                    display: flex;
                    gap: 8px;
                }
                .courses-table {
                    border: 1px solid var(--border);
                    border-radius: var(--radius-sm);
                    overflow: hidden;
                }
                .table-header {
                    display: grid;
                    grid-template-columns: 80px 1fr 50px 60px 120px 70px 80px;
                    gap: 8px;
                    padding: 10px 12px;
                    background: var(--surface-2);
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    color: var(--text-muted);
                    font-weight: 600;
                }
                .table-row {
                    display: grid;
                    grid-template-columns: 80px 1fr 50px 60px 120px 70px 80px;
                    gap: 8px;
                    padding: 10px 12px;
                    border-top: 1px solid var(--border);
                    align-items: center;
                    font-size: 0.9rem;
                }
                .table-row.unverified {
                    background: rgba(234, 179, 8, 0.1);
                }
                .table-row input,
                .table-row select {
                    padding: 4px 6px;
                    border: 1px solid var(--border);
                    border-radius: var(--radius-sm);
                    background: var(--surface);
                    color: var(--text);
                    font-size: 0.85rem;
                }
                .edit-input.small {
                    width: 50px;
                }
                .mono {
                    font-family: monospace;
                    font-weight: 600;
                }
                .course-name {
                    color: var(--text-muted);
                    font-size: 0.85rem;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }
                .grade {
                    font-weight: 700;
                }
                .grade-A, .grade-A- { color: #22c55e; }
                .grade-B\\+, .grade-B, .grade-B- { color: #3b82f6; }
                .grade-C\\+, .grade-C, .grade-C- { color: #eab308; }
                .grade-D\\+, .grade-D, .grade-F { color: #ef4444; }
                .grade-W { color: #9ca3af; }
                .status-badge {
                    padding: 2px 8px;
                    border-radius: 100px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    text-align: center;
                }
                .status-badge.verified {
                    background: rgba(34, 197, 94, 0.2);
                    color: #22c55e;
                }
                .status-badge.unverified {
                    background: rgba(234, 179, 8, 0.2);
                    color: #eab308;
                }
                .row-actions {
                    display: flex;
                    gap: 4px;
                }
                .btn-icon {
                    background: none;
                    border: 1px solid var(--border);
                    border-radius: var(--radius-sm);
                    padding: 4px 8px;
                    cursor: pointer;
                    font-size: 0.8rem;
                }
                .btn-icon:hover {
                    background: var(--surface-2);
                }
                .btn-icon.delete:hover {
                    background: rgba(239, 68, 68, 0.2);
                    border-color: #ef4444;
                }
            `}</style>
        </div>
    )
}

export default CourseEditor
