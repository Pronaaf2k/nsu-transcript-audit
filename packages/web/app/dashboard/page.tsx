'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'
import ScanHistoryTable from '@/components/ScanHistoryTable'
import { createClient } from '@/lib/supabase/client'

type Scan = {
    id: string
    created_at: string
    program: string
    total_credits: number
    cgpa: number
    graduation_status: string
    source_type: string
}

export default function DashboardPage() {
    const router = useRouter()
    const supabase = createClient()
    const [userEmail, setUserEmail] = useState<string | undefined>()
    const [scans, setScans] = useState<Scan[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let mounted = true

        async function load() {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) {
                router.replace('/login')
                return
            }
            if (!mounted) return
            setUserEmail(session.user.email)

            const apiUrl = process.env.NEXT_PUBLIC_API_URL
            if (!apiUrl) {
                setLoading(false)
                return
            }

            const res = await fetch(`${apiUrl}/history?limit=50`, {
                headers: { Authorization: `Bearer ${session.access_token}` }
            })
            if (!mounted) return
            if (!res.ok) {
                setLoading(false)
                return
            }

            const data = await res.json()
            setScans(
                Array.isArray(data)
                    ? data.map((scan) => ({
                        ...scan,
                        source_type: scan?.source_type ?? 'unknown'
                    }))
                    : []
            )
            setLoading(false)
        }

        load()
        return () => { mounted = false }
    }, [router, supabase])

    const { totalScans, passCount, failCount } = useMemo(() => {
        const total = scans.length
        const pass = scans.filter(s => s.graduation_status === 'PASS').length
        const fail = scans.filter(s => s.graduation_status === 'FAIL').length
        return { totalScans: total, passCount: pass, failCount: fail }
    }, [scans])

    return (
        <>
            <Nav user={userEmail ? { email: userEmail } : undefined} />
            <div className="container">
                <div className="page-header">
                    <h1>Dashboard</h1>
                    <p>Your transcript audit history and quick actions</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '32px' }}>
                    <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
                        <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent)' }}>{totalScans}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', marginTop: '4px' }}>Total Audits</div>
                    </div>
                    <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
                        <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--success)' }}>{passCount}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', marginTop: '4px' }}>Eligible</div>
                    </div>
                    <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
                        <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--danger)' }}>{failCount}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', marginTop: '4px' }}>Not Eligible</div>
                    </div>
                    <div className="card" style={{ textAlign: 'center', padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '12px' }}>
                        <Link href="/scan" className="btn btn-outline" style={{ width: '100%' }}>
                            ◉ Scan & Audit
                        </Link>
                    </div>
                </div>

                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px' }}>Recent Audits</h2>

                {loading ? (
                    <div className="card" style={{ textAlign: 'center', padding: '40px' }}>Loading history…</div>
                ) : scans.length > 0 ? (
                    <ScanHistoryTable scans={scans} />
                ) : (
                    <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📄</div>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>No scans yet.</p>
                        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                            <Link href="/scan" className="btn btn-primary">◉ Scan & Audit</Link>
                        </div>
                    </div>
                )}
            </div>
            <Footer />
        </>
    )
}
