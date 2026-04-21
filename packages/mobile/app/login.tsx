import { useState } from 'react'
import { ActivityIndicator, Alert, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { Redirect } from 'expo-router'
import { signInWithGoogle, useAuthSession } from '../lib/auth'

export default function LoginScreen() {
    const { session, loading, isConfigured, configError } = useAuthSession()
    const [submitting, setSubmitting] = useState(false)

    async function handleLogin() {
        setSubmitting(true)
        try {
            await signInWithGoogle()
        } catch (error: unknown) {
            Alert.alert('Login Failed', error instanceof Error ? error.message : String(error))
        } finally {
            setSubmitting(false)
        }
    }

    if (loading) {
        return (
            <View style={s.container}>
                <ActivityIndicator color="#e5dfd5" />
            </View>
        )
    }

    if (session) {
        return <Redirect href={'/(tabs)/scan' as never} />
    }

    return (
        <View style={s.container}>
            <View style={s.shell}>
                <View style={s.logo}>
                    <Text style={s.logoText}>NSU</Text>
                </View>

                <Text style={s.eyebrow}>Welcome to NSU Audit</Text>
                <Text style={s.title}>{`Sign in to\nyour audit.`}</Text>
                <Text style={s.subtitle}>One account. Shared transcript history across web and mobile.</Text>

                {!isConfigured && (
                    <View style={s.errorCard}>
                        <Text style={s.errorTitle}>Configuration Error</Text>
                        <Text style={s.errorText}>{configError}</Text>
                    </View>
                )}

                <TouchableOpacity style={[s.primaryButton, (!isConfigured || submitting) && s.primaryButtonDisabled]} onPress={handleLogin} disabled={!isConfigured || submitting}>
                    {submitting ? <ActivityIndicator color="#121315" /> : <Text style={s.primaryButtonText}>Sign in with North South account</Text>}
                </TouchableOpacity>

                <Text style={s.footer}>North South University Degree Audit System</Text>
            </View>
        </View>
    )
}

const s = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: 'center',
        backgroundColor: '#060709',
        paddingHorizontal: 24,
    },
    shell: {
        alignItems: 'center',
    },
    logo: {
        width: 98,
        height: 98,
        marginBottom: 20,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: '#2c2f38',
        backgroundColor: '#111319',
        alignItems: 'center',
        justifyContent: 'center',
    },
    logoText: {
        color: '#ece7df',
        fontSize: 42,
        fontWeight: '700',
    },
    eyebrow: {
        color: '#a9a299',
        letterSpacing: 2,
        fontSize: 12,
        textTransform: 'uppercase',
        marginBottom: 16,
    },
    title: {
        color: '#ece7df',
        fontSize: 48,
        lineHeight: 50,
        textAlign: 'center',
        marginBottom: 14,
    },
    subtitle: {
        color: '#b5aea5',
        fontSize: 15,
        textAlign: 'center',
        marginBottom: 24,
        maxWidth: 360,
    },
    errorCard: {
        width: '100%',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#7f1d1d',
        backgroundColor: '#1f1215',
        padding: 16,
        marginBottom: 16,
    },
    errorTitle: {
        color: '#fecaca',
        fontWeight: '700',
        marginBottom: 6,
    },
    errorText: {
        color: '#fca5a5',
    },
    primaryButton: {
        width: '100%',
        maxWidth: 430,
        borderRadius: 9,
        borderWidth: 1,
        borderColor: '#3a3c42',
        backgroundColor: '#e5dfd5',
        paddingVertical: 14,
        paddingHorizontal: 18,
        alignItems: 'center',
        justifyContent: 'center',
    },
    primaryButtonDisabled: {
        opacity: 0.6,
    },
    primaryButtonText: {
        color: '#121315',
        fontWeight: '800',
        letterSpacing: 1,
        textTransform: 'uppercase',
        fontSize: 13,
    },
    footer: {
        marginTop: 26,
        color: '#7f7a71',
        fontSize: 14,
        textAlign: 'center',
    },
})
