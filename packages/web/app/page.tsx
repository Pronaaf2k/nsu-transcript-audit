'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export default function HomePage() {
  const supabase = createClient()
  const [email, setEmail] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return
      setEmail(data.session?.user?.email ?? null)
      setLoading(false)
    })
    return () => {
      mounted = false
    }
  }, [supabase])

  async function signInWithGoogle() {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${location.origin}/auth/callback` },
    })
  }

  async function signOut() {
    await supabase.auth.signOut()
    setEmail(null)
  }

  return (
    <main
      style={{
        minHeight: '100vh',
        background:
          'radial-gradient(1100px 520px at 12% -8%, rgba(64, 34, 18, 0.4) 0%, transparent 60%), radial-gradient(900px 500px at 84% 8%, rgba(34, 44, 86, 0.4) 0%, transparent 60%), #060709',
        color: '#ece7df',
      }}
    >
      <div style={{ maxWidth: 980, margin: '0 auto', padding: '72px 24px' }}>
        <section
          style={{
            maxWidth: 520,
            margin: '70px auto 0',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: 98,
              height: 98,
              margin: '0 auto 20px',
              borderRadius: 20,
              border: '1px solid #2c2f38',
              background: 'linear-gradient(135deg, #1a1d25 0%, #111319 100%)',
              display: 'grid',
              placeItems: 'center',
              fontSize: 42,
            }}
          >
            <span aria-label="audit" style={{ fontFamily: 'Georgia, Times New Roman, serif', fontWeight: 700 }}>NSU</span>
          </div>

          <p
            style={{
              margin: 0,
              color: '#a9a299',
              letterSpacing: '0.18em',
              fontSize: 12,
              textTransform: 'uppercase',
            }}
          >
            Welcome to NSU Audit
          </p>

          <h1
            style={{
              margin: '16px 0 14px',
              fontSize: 66,
              lineHeight: 1.02,
              fontWeight: 500,
              fontFamily: 'Georgia, Times New Roman, serif',
            }}
          >
            Sign in to
            <br />
            <em style={{ fontStyle: 'italic' }}>your audit.</em>
          </h1>

          <p style={{ color: '#b5aea5', marginTop: 0, marginBottom: 24 }}>
            One account. Shared transcript history across web and CLI.
          </p>

          {loading ? (
            <p style={{ color: '#b5aea5' }}>Checking session...</p>
          ) : email ? (
            <div style={{ display: 'grid', gap: 12 }}>
              <Link
                href="/scan"
                style={{
                  display: 'inline-block',
                  textDecoration: 'none',
                  borderRadius: 9,
                  border: '1px solid #3a3c42',
                  background: '#e5dfd5',
                  color: '#121315',
                  fontWeight: 800,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  padding: '14px 18px',
                  fontSize: 13,
                }}
              >
                Open Audit Workspace
              </Link>
              <button
                onClick={signOut}
                style={{
                  borderRadius: 9,
                  border: '1px solid #343841',
                  background: 'transparent',
                  color: '#d3cdc3',
                  fontWeight: 700,
                  padding: '10px 14px',
                  cursor: 'pointer',
                }}
              >
                Logout ({email})
              </button>
            </div>
          ) : (
            <button
              onClick={signInWithGoogle}
              style={{
                width: '100%',
                maxWidth: 430,
                borderRadius: 9,
                border: '1px solid #3a3c42',
                background: '#e5dfd5',
                color: '#121315',
                fontWeight: 800,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                padding: '14px 18px',
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              Sign in with North South account
            </button>
          )}

          <p style={{ marginTop: 26, color: '#7f7a71', fontSize: 14 }}>
            North South University � Degree Audit System
          </p>
        </section>
      </div>
    </main>
  )
}
