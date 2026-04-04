'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'
import TranscriptUpload from '@/components/TranscriptUpload'
import AuditReport from '@/components/AuditReport'
import { createClient } from '@/lib/supabase/client'

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

export default function ScanPage() {
    const supabase = createClient()
    const router = useRouter()
    const [program, setProgram] = useState('')
    const [fileSelected, setFileSelected] = useState(false)
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
        setFileSelected(true)
        
        try {
            const formData = new FormData()
            formData.append('file', file)
            formData.append('program', program)

            let endpoint = 'http://localhost:8000/audit/image'
            if (file.name.endsWith('.csv')) {
                 endpoint = 'http://localhost:8000/audit/csv'
            }

            const res = await fetch(endpoint, {
                method: 'POST',
                body: formData,
            })
            
            const json = await res.json()
            if (!res.ok) throw new Error(json.detail ?? 'Audit failed')
            setResult(json)
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e))
            setFileSelected(false)
        } finally {
            setLoading(false)
        }
    }

    return (
        <>
            <Nav />
            <div className="container">
                <div className="page-header">
                    <h1>New Scan</h1>
                    <p>Upload a transcript image, PDF, or CSV to run a graduation audit.</p>
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
                        {!program && (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '8px' }}>
                                Please select your program before uploading
                            </p>
                        )}
                    </div>
                    
                    <div style={{ marginTop: '24px' }}>
                        <label style={{ fontWeight: 600, marginBottom: '12px', display: 'block' }}>
                            2. Upload Transcript
                        </label>
                        <div style={{ 
                            padding: '24px', 
                            border: `2px dashed ${program ? 'var(--border)' : 'var(--text-muted)'}`, 
                            borderRadius: 'var(--radius)',
                            opacity: program ? 1 : 0.5,
                            pointerEvents: program ? 'auto' : 'none'
                        }}>
                            <TranscriptUpload onUpload={handleUpload} loading={loading} />
                        </div>
                        {!program && (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '8px', textAlign: 'center' }}>
                                Select a program first to enable upload
                            </p>
                        )}
                    </div>
                    
                    {fileSelected && !result && !error && (
                        <div style={{ marginTop: '20px', padding: '16px', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                            <p style={{ color: 'var(--accent)', fontWeight: 600 }}>Processing transcript...</p>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
                                This may take a few moments
                            </p>
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
                        <div style={{ marginTop: '16px', textAlign: 'right', display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                            <button className="btn btn-outline" onClick={() => { setResult(null); setFileSelected(false); }}>
                                Scan Another
                            </button>
                            <button className="btn btn-outline" onClick={() => router.push('/dashboard')}>
                                ← Back to Dashboard
                            </button>
                        </div>
                    </div>
                )}
            </div>
            <Footer />
        </>
    )
}
