'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

export default function Nav({ user }: { user?: { email?: string } }) {
    const supabase = createClient()
    const router = useRouter()

    async function signOut() {
        await supabase.auth.signOut()
        router.push('/login')
        router.refresh()
    }

    return (
        <nav className="nav">
            <div className="container nav-inner">
                <Link href="/dashboard" className="nav-logo">NSU <span>Audit</span></Link>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <Link href="/scan" className="btn btn-outline" style={{ padding: '6px 14px', fontSize: '0.88rem' }}>+ New Scan</Link>
                    {user?.email && (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>{user.email}</span>
                    )}
                    <button id="signout-btn" className="btn btn-outline" style={{ padding: '6px 14px', fontSize: '0.88rem' }} onClick={signOut}>
                        Sign Out
                    </button>
                </div>
            </div>
        </nav>
    )
}
