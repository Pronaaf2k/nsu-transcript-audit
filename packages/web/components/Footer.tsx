'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV_ITEMS = [
    { href: '/dashboard', label: 'Dashboard', icon: '◈' },
    { href: '/audit', label: 'Audit Engine', icon: '◉' },
    { href: '/scan', label: 'New Scan', icon: '+' },
]

export default function Footer() {
    return (
        <footer className="footer">
            <div className="container footer-inner">
                <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                    <span className="footer-logo">NSU <span>Audit</span></span>
                    <div className="footer-links">
                        {NAV_ITEMS.map((item) => (
                            <Link key={item.href} href={item.href} className="footer-link">
                                {item.label}
                            </Link>
                        ))}
                    </div>
                </div>
                <div className="footer-copy">
                    Built for North South University Students
                </div>
            </div>
            <style>{`
                .footer {
                    border-top: 1px solid var(--border);
                    padding: 24px 0;
                    margin-top: 60px;
                    background: var(--surface);
                }
                .footer-inner {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 16px;
                }
                .footer-logo {
                    font-weight: 800;
                    font-size: 1rem;
                    color: var(--text);
                }
                .footer-logo span {
                    color: var(--accent);
                }
                .footer-links {
                    display: flex;
                    gap: 16px;
                }
                .footer-link {
                    color: var(--text-muted);
                    font-size: 0.85rem;
                    text-decoration: none;
                }
                .footer-link:hover {
                    color: var(--text);
                    text-decoration: underline;
                }
                .footer-copy {
                    color: var(--text-muted);
                    font-size: 0.8rem;
                }
                @media (max-width: 768px) {
                    .footer-inner {
                        flex-direction: column;
                        text-align: center;
                    }
                }
            `}</style>
        </footer>
    )
}
