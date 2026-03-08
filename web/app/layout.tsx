import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
    title: 'NSU Transcript Audit',
    description: 'Automated graduation audit for North South University students',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    )
}
