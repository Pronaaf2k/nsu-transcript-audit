import { useEffect, useState } from 'react'
import * as WebBrowser from 'expo-web-browser'
import { makeRedirectUri } from 'expo-auth-session'
import type { Session } from '@supabase/supabase-js'
import { supabase, SUPABASE_CONFIG_ERROR } from './supabase'

WebBrowser.maybeCompleteAuthSession()

export function useAuthSession() {
    const [session, setSession] = useState<Session | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (!supabase) {
            setSession(null)
            setLoading(false)
            return
        }

        let mounted = true

        supabase.auth.getSession().then(({ data }) => {
            if (!mounted) return
            setSession(data.session)
            setLoading(false)
        })

        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
            if (!mounted) return
            setSession(nextSession)
            setLoading(false)
        })

        return () => {
            mounted = false
            subscription.unsubscribe()
        }
    }, [])

    return { session, loading, isConfigured: Boolean(supabase), configError: SUPABASE_CONFIG_ERROR }
}

export async function signInWithGoogle() {
    if (!supabase) {
        throw new Error(SUPABASE_CONFIG_ERROR ?? 'Supabase is not configured')
    }

    const redirectTo = makeRedirectUri({ scheme: 'nsu-audit' })
    const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo,
            skipBrowserRedirect: true,
        },
    })

    if (error) throw error
    if (!data?.url) throw new Error('Could not start Google sign-in')

    const result = await WebBrowser.openAuthSessionAsync(data.url, redirectTo)

    if (result.type !== 'success' || !result.url) {
        throw new Error('Google sign-in was cancelled')
    }

    const params = new URL(result.url.replace('#', '?')).searchParams
    const access_token = params.get('access_token')
    const refresh_token = params.get('refresh_token')

    if (!access_token || !refresh_token) {
        throw new Error('Google sign-in did not return a session')
    }

    const { error: sessionError } = await supabase.auth.setSession({ access_token, refresh_token })

    if (sessionError) throw sessionError
}

export async function signOut() {
    if (!supabase) return
    const { error } = await supabase.auth.signOut()
    if (error) throw error
}
