import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import Nav from '@/components/Nav'
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

    return (
        <>
            <Nav user={user} />
            <div className="container">
                <div className="page-header">
                    <h1>Dashboard</h1>
                    <p>Your transcript scan history</p>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}>
                    <Link href="/scan" className="btn btn-primary" id="new-scan-btn">
                        + New Scan
                    </Link>
                </div>

                {scans && scans.length > 0
                    ? <ScanHistoryTable scans={scans} />
                    : (
                        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
                            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📄</div>
                            <p style={{ color: 'var(--text-muted)' }}>No scans yet. <Link href="/scan">Upload your first transcript →</Link></p>
                        </div>
                    )
                }
            </div>
        </>
    )
}
