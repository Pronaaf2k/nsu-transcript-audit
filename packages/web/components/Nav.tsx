'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'

const NAV_ITEMS = [
    { href: '/dashboard', label: 'Dashboard', icon: '◈' },
    { href: '/audit', label: 'Audit Engine', icon: '◉' },
    { href: '/scan', label: 'New Scan', icon: '+' },
]

type WakeStatus = 'idle' | 'waking' | 'awake' | 'error'

export default function Nav({ user }: { user?: { email?: string } }) {
    const supabase = createClient()
    const router = useRouter()
    const pathname = usePathname()
    const [wakeStatus, setWakeStatus] = useState<WakeStatus>('idle')
    const [wakeLabel, setWakeLabel] = useState('⚡ Wake Backend')

    async function signOut() {
        await supabase.auth.signOut()
        router.push('/login')
        router.refresh()
    }

    async function wakeBackend() {
        if (wakeStatus === 'waking') return
        setWakeStatus('waking')
        setWakeLabel('⏳ Starting...')
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`, {
                signal: AbortSignal.timeout(60000)
            })
            if (res.ok) {
                setWakeStatus('awake')
                setWakeLabel('✅ Backend Ready')
                setTimeout(() => {
                    setWakeStatus('idle')
                    setWakeLabel('⚡ Wake Backend')
                }, 5000)
            } else {
                throw new Error('Bad response')
            }
        } catch {
            setWakeStatus('error')
            setWakeLabel('❌ Failed — Retry')
            setTimeout(() => {
                setWakeStatus('idle')
                setWakeLabel('⚡ Wake Backend')
            }, 4000)
        }
    }

    const wakeBtnStyle: React.CSSProperties = {
        padding: '6px 14px',
        fontSize: '0.8rem',
        fontFamily: 'monospace',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid',
        cursor: wakeStatus === 'waking' ? 'not-allowed' : 'pointer',
        transition: 'all 0.2s ease',
        fontWeight: 600,
        ...(wakeStatus === 'idle'    ? { borderColor: 'var(--border)', color: 'var(--text-muted)', background: 'transparent' } :
            wakeStatus === 'waking' ? { borderColor: '#854d0e', color: '#fde047', background: 'rgba(133,77,14,0.2)' } :
            wakeStatus === 'awake'  ? { borderColor: '#166534', color: '#86efac', background: 'rgba(22,101,52,0.2)' } :
                                      { borderColor: '#991b1b', color: '#fca5a5', background: 'rgba(153,27,27,0.2)' })
    }

    return (
        <nav className="nav">
            <div className="container nav-inner">
                <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
                    <Link href="/dashboard" className="nav-logo">
                        NSU <span>Audit</span>
                    </Link>
                    <div className="nav-links">
                        {NAV_ITEMS.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`nav-link ${pathname === item.href ? 'active' : ''}`}
                            >
                                <span className="nav-icon">{item.icon}</span>
                                {item.label}
                            </Link>
                        ))}
                    </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button onClick={wakeBackend} style={wakeBtnStyle} title="Wake up the Render backend from cold start">
                        {wakeLabel}
                    </button>
                    {user?.email && (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                            {user.email}
                        </span>
                    )}
                    <button
                        id="signout-btn"
                        className="btn btn-outline"
                        style={{ padding: '6px 14px', fontSize: '0.85rem' }}
                        onClick={signOut}
                    >
                        Sign Out
                    </button>
                </div>
            </div>

            <style>{`
                .nav-links { display: flex; align-items: center; gap: 4px; }
                .nav-link {
                    display: flex; align-items: center; gap: 6px;
                    padding: 8px 16px; border-radius: var(--radius-sm);
                    color: var(--text-muted); font-size: 0.9rem; font-weight: 500;
                    text-decoration: none; transition: all 0.15s ease;
                }
                .nav-link:hover { color: var(--text); background: var(--surface-2); text-decoration: none; }
                .nav-link.active { color: var(--accent); background: rgba(99,102,241,0.15); }
                .nav-icon { font-size: 1rem; opacity: 0.7; }
                .nav-link.active .nav-icon { opacity: 1; }
                @media (max-width: 768px) {
                    .nav-links { display: none; }
                }
            `}</style>
        </nav>
    )
}
