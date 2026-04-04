'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

const NAV_ITEMS = [
    { href: '/dashboard', label: 'Dashboard', icon: '◈' },
    { href: '/audit', label: 'Audit Engine', icon: '◉' },
    { href: '/scan', label: 'New Scan', icon: '+' },
]

export default function Nav({ user }: { user?: { email?: string } }) {
    const supabase = createClient()
    const router = useRouter()
    const pathname = usePathname()

    async function signOut() {
        await supabase.auth.signOut()
        router.push('/login')
        router.refresh()
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

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
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
                .nav-links {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                .nav-link {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    padding: 8px 16px;
                    border-radius: var(--radius-sm);
                    color: var(--text-muted);
                    font-size: 0.9rem;
                    font-weight: 500;
                    text-decoration: none;
                    transition: all 0.15s ease;
                }
                .nav-link:hover {
                    color: var(--text);
                    background: var(--surface-2);
                    text-decoration: none;
                }
                .nav-link.active {
                    color: var(--accent);
                    background: rgba(99, 102, 241, 0.15);
                }
                .nav-icon {
                    font-size: 1rem;
                    opacity: 0.7;
                }
                .nav-link.active .nav-icon {
                    opacity: 1;
                }

                @media (max-width: 768px) {
                    .nav-links {
                        display: none;
                    }
                    .nav-links.show {
                        display: flex;
                        flex-direction: column;
                        position: absolute;
                        top: 60px;
                        left: 0;
                        right: 0;
                        background: var(--surface);
                        border-bottom: 1px solid var(--border);
                        padding: 16px;
                        gap: 8px;
                    }
                }
            `}</style>
        </nav>
    )
}
