import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'
import ScanHistoryTable from '@/components/ScanHistoryTable'

export default async function DashboardPage() {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) redirect('/login')

    const { data: scans } = await supabase
        .from('transcript_scans')
        .select('id, created_at, source_type, file_name, program, total_credits, cgpa, graduation_status')
        .order('created_at', { ascending: false })
        .limit(50)

    const totalScans = scans?.length || 0
    const passCount = scans?.filter(s => s.graduation_status === 'PASS').length || 0
    const failCount = scans?.filter(s => s.graduation_status === 'FAIL').length || 0

    return (
        <>
            <Nav user={user} />
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
                        <Link href="/audit" className="btn btn-primary" style={{ width: '100%' }}>
                            ◉ Audit Engine
                        </Link>
                        <Link href="/scan" className="btn btn-outline" style={{ width: '100%' }}>
                            + New Scan
                        </Link>
                    </div>
                </div>

                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px' }}>Recent Audits</h2>

                {scans && scans.length > 0
                    ? <ScanHistoryTable scans={scans} />
                    : (
                        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
                            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📄</div>
                            <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>No scans yet.</p>
                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                                <Link href="/scan" className="btn btn-primary">+ New Scan</Link>
                                <Link href="/audit" className="btn btn-outline">Use Audit Engine</Link>
                            </div>
                        </div>
                    )
                }
            </div>
            <Footer />
        </>
    )
}
