'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/Nav'
import TranscriptUpload from '@/components/TranscriptUpload'
import AuditReport from '@/components/AuditReport'
import { createClient } from '@/lib/supabase/client'

const PROGRAMS = ['CSE', 'BBA', 'EEE', 'ECE', 'BBA_ACC', 'ENG', 'PHY', 'MATH']

export default function ScanPage() {
    const supabase = createClient()
    const router = useRouter()
    const [program, setProgram] = useState('CSE')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [result, setResult] = useState<Record<string, unknown> | null>(null)

    async function handleUpload(file: File) {
        setError(null)
        setLoading(true)
        try {
            const { data: { user } } = await supabase.auth.getUser()
            if (!user) throw new Error('Not authenticated')

            const { data: { session } } = await supabase.auth.getSession()
            const token = session?.access_token

            let body: Record<string, unknown>

            if (file.name.endsWith('.csv')) {
                const csv_text = await file.text()
                body = { csv_text, program, file_name: file.name }
            } else {
                // Upload to Storage first
                const path = `${user.id}/${Date.now()}-${file.name}`
                const { error: upErr } = await supabase.storage.from('transcripts').upload(path, file)
                if (upErr) throw upErr
                body = { storage_path: path, source_type: file.type.includes('pdf') ? 'pdf' : 'image', program, file_name: file.name }
            }

            const res = await fetch(
                `${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/process-transcript`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                    body: JSON.stringify(body),
                }
            )
            const json = await res.json()
            if (!res.ok) throw new Error(json.error ?? 'Audit failed')
            setResult(json.scan)
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e))
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
                        <label htmlFor="program-select">Program</label>
                        <select id="program-select" value={program} onChange={e => setProgram(e.target.value)}>
                            {PROGRAMS.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>
                    <TranscriptUpload onUpload={handleUpload} loading={loading} />
                    {error && <p style={{ color: 'var(--danger)', marginTop: '16px' }}>⚠ {error}</p>}
                </div>

                {result && (
                    <div className="animate-in">
                        <AuditReport scan={result} />
                        <div style={{ marginTop: '16px', textAlign: 'right' }}>
                            <button className="btn btn-outline" onClick={() => router.push('/dashboard')}>← Back to Dashboard</button>
                        </div>
                    </div>
                )}
            </div>
        </>
    )
}
