import { useEffect, useState } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, ScrollView } from 'react-native'
import * as DocumentPicker from 'expo-document-picker'
import { supabase } from '../../lib/supabase'

const PROGRAMS = [
    { code: 'CSE', label: 'CSE' },
    { code: 'BBA', label: 'BBA (2014+)' },
    { code: 'BBA-OLD', label: 'BBA-OLD (pre-2014)' },
    { code: 'ETE', label: 'ETE' },
    { code: 'ENV', label: 'ENV' },
    { code: 'ENG', label: 'ENG' },
    { code: 'ECO', label: 'ECO' },
] as const

const LEVELS = ['1', '2', '3'] as const
const MODES = [
    { key: 'csv', label: 'Run CSV Audit' },
    { key: 'ocr', label: 'Scan OCR (PDF/Image)' },
] as const

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? ''

type HistoryRow = {
    id: string
    created_at: string
    program: string
    total_credits: number | null
    cgpa: number | null
    graduation_status: string
}

type AuditResult = {
    id?: string
    program?: string
    total_credits?: number
    cgpa?: number
    graduation_status?: string
    audit_level?: number
    program_used?: string
    program_requested?: string
    program_inference_confidence?: number
    audit_result?: {
        gradtrace?: {
            level_2?: { standing?: string }
            level_3?: {
                total_credits_required?: number
                remaining?: Record<string, Record<string, number>>
                missing?: Record<string, string[]>
            }
        }
    }
}

export default function ScanScreen() {
    const [program, setProgram] = useState('CSE')
    const [auditLevel, setAuditLevel] = useState<typeof LEVELS[number]>('3')
    const [mode, setMode] = useState<typeof MODES[number]['key']>('csv')
    const [userEmail, setUserEmail] = useState('')
    const [history, setHistory] = useState<HistoryRow[]>([])
    const [historyLoading, setHistoryLoading] = useState(false)
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<AuditResult | null>(null)

    useEffect(() => {
        let mounted = true
        supabase.auth.getSession().then(async ({ data }) => {
            if (!mounted) return
            setUserEmail(data.session?.user?.email ?? '')
            const token = data.session?.access_token
            if (token) {
                await loadHistory(token)
            }
        })
        return () => {
            mounted = false
        }
    }, [])

    async function loadHistory(existingToken?: string) {
        setHistoryLoading(true)
        try {
            const token = existingToken ?? (await supabase.auth.getSession()).data.session?.access_token
            if (!token || !API_URL) {
                setHistory([])
                return
            }
            const res = await fetch(`${API_URL}/history?limit=20`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) {
                setHistory([])
                return
            }
            const data = await res.json()
            setHistory(Array.isArray(data) ? data : [])
        } finally {
            setHistoryLoading(false)
        }
    }

    async function logout() {
        await supabase.auth.signOut()
        setResult(null)
        setHistory([])
        setUserEmail('')
        Alert.alert('Logged out')
    }

    async function pickAndScan() {
        const picked = await DocumentPicker.getDocumentAsync({
            type: ['application/pdf', 'image/*', 'text/csv', 'text/comma-separated-values'],
            copyToCacheDirectory: true,
        })
        if (picked.canceled) return

        const file = picked.assets[0]
        setLoading(true)
        setResult(null)

        try {
            const { data: { session } } = await supabase.auth.getSession()
            const token = session?.access_token
            if (!token) throw new Error('Not authenticated')
            if (!API_URL) throw new Error('EXPO_PUBLIC_API_URL is not set')

            let res: Response
            if (mode === 'csv') {
                const resp = await fetch(file.uri)
                const csv_text = await resp.text()
                res = await fetch(`${API_URL}/audit/run_csv`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ csv_text, program, audit_level: Number(auditLevel) }),
                })
            } else {
                const form = new FormData()
                form.append('program', program)
                form.append('audit_level', auditLevel)
                form.append('file', {
                    uri: file.uri,
                    name: file.name ?? 'transcript',
                    type: file.mimeType ?? 'application/octet-stream',
                } as never)
                res = await fetch(`${API_URL}/audit/image`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${token}` },
                    body: form,
                })
            }

            const json = await res.json()
            if (!res.ok) throw new Error(json.detail ?? 'Audit failed')
            setResult(json)
            await loadHistory(token)
        } catch (e: unknown) {
            Alert.alert('Error', e instanceof Error ? e.message : String(e))
        } finally {
            setLoading(false)
        }
    }

    const status = result?.graduation_status
    const statusColor = status === 'PASS' ? '#22c55e' : status === 'FAIL' ? '#f43f5e' : '#a78bfa'
    const standing = result?.audit_result?.gradtrace?.level_2?.standing ?? 'UNKNOWN'
    const remaining = result?.audit_result?.gradtrace?.level_3?.remaining ?? null
    const missing = result?.audit_result?.gradtrace?.level_3?.missing ?? null
    const totalRequired = result?.audit_result?.gradtrace?.level_3?.total_credits_required ?? 0
    const remainingCount = remaining
        ? Object.values(remaining).reduce((acc, group) => acc + Object.keys(group ?? {}).length, 0)
        : (missing ? Object.values(missing).reduce((acc, items) => acc + (Array.isArray(items) ? items.length : 0), 0) : 0)

    const snapshotRows = [
        ['Status', status ?? 'PENDING'],
        ['Program', result?.program_used ?? result?.program ?? program],
        ['Audit Level', `L${result?.audit_level ?? Number(auditLevel)}`],
        ['Credits', String(result?.total_credits ?? '—')],
        ['CGPA', result?.cgpa?.toFixed ? result.cgpa.toFixed(2) : String(result?.cgpa ?? '—')],
        ['Scan ID', result?.id ?? '—'],
    ] as const

    return (
        <ScrollView style={s.container} contentContainerStyle={{ padding: 16 }}>
            <View style={s.headerRow}>
                <Text style={s.headerTitle}>New Audit</Text>
                <TouchableOpacity style={s.logoutBtn} onPress={logout}>
                    <Text style={s.logoutText}>Logout</Text>
                </TouchableOpacity>
            </View>
            {!!userEmail && <Text style={s.userText}>{userEmail}</Text>}

            <Text style={s.label}>Program</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 20 }}>
                {PROGRAMS.map(p => (
                    <TouchableOpacity key={p.code} style={[s.chip, program === p.code && s.chipActive]} onPress={() => setProgram(p.code)}>
                        <Text style={[s.chipText, program === p.code && s.chipTextActive]}>{p.label}</Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            <Text style={s.label}>Audit Level</Text>
            <View style={s.inlineRow}>
                {LEVELS.map(level => (
                    <TouchableOpacity key={level} style={[s.chip, auditLevel === level && s.chipActive]} onPress={() => setAuditLevel(level)}>
                        <Text style={[s.chipText, auditLevel === level && s.chipTextActive]}>Level {level}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            <Text style={s.label}>Mode</Text>
            <View style={[s.inlineRow, { marginBottom: 20 }]}> 
                {MODES.map(m => (
                    <TouchableOpacity key={m.key} style={[s.chip, mode === m.key && s.chipActive]} onPress={() => setMode(m.key)}>
                        <Text style={[s.chipText, mode === m.key && s.chipTextActive]}>{m.label}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            <TouchableOpacity style={s.uploadBtn} onPress={pickAndScan} disabled={loading}>
                {loading
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={s.uploadBtnText}>Select Transcript File</Text>
                }
            </TouchableOpacity>

            {result && (
                <>
                    <View style={s.card}>
                        <Text style={s.cardTitle}>Audit Snapshot</Text>
                        {snapshotRows.map(([k, v]) => (
                            <View key={k} style={s.tableRow}>
                                <Text style={s.tableKey}>{k}</Text>
                                <Text style={[s.tableVal, k === 'Status' && { color: statusColor }]}>{v}</Text>
                            </View>
                        ))}
                        {result.program_requested && result.program_used && result.program_requested !== result.program_used && (
                            <Text style={s.warnText}>
                                OCR switched program from {result.program_requested} to {result.program_used} ({Math.round((result.program_inference_confidence ?? 0) * 100)}% confidence)
                            </Text>
                        )}
                    </View>

                    <View style={s.banner}> 
                        <View>
                            <Text style={[s.bannerTitle, { color: statusColor }]}>{status === 'PASS' ? 'Eligible' : status === 'FAIL' ? 'Not Eligible' : 'Pending'}</Text>
                            <Text style={s.bannerSub}>for graduation</Text>
                        </View>
                        <View style={{ alignItems: 'flex-end' }}>
                            <Text style={s.bannerCgpa}>{result.cgpa?.toFixed ? result.cgpa.toFixed(2) : result.cgpa ?? '—'}</Text>
                            <Text style={s.bannerSub}>{result.total_credits ?? 0} / {totalRequired || '—'} credits</Text>
                        </View>
                    </View>

                    <View style={s.card}>
                        <Text style={s.cardTitle}>Student Standing</Text>
                        <Text style={s.meta}>Academic standing: <Text style={{ color: '#22c55e', fontWeight: '700' }}>{standing}</Text></Text>
                        <Text style={s.meta}>Missing courses: <Text style={{ fontWeight: '700', color: '#e8eaf3' }}>{remainingCount}</Text></Text>

                        {remaining && Object.keys(remaining).length > 0 && Object.entries(remaining).map(([group, items]) => (
                            <View key={group} style={s.missingRow}>
                                <Text style={s.missingText}><Text style={{ color: '#f8fafc', fontWeight: '700' }}>{group}:</Text> {Object.keys(items ?? {}).join(', ') || 'None'}</Text>
                            </View>
                        ))}

                        {(!remaining || Object.keys(remaining).length === 0) && missing && Object.keys(missing).length > 0 && Object.entries(missing).map(([group, items]) => (
                            <View key={group} style={s.missingRow}>
                                <Text style={s.missingText}><Text style={{ color: '#f8fafc', fontWeight: '700' }}>{group}:</Text> {Array.isArray(items) && items.length > 0 ? items.join(', ') : 'None'}</Text>
                            </View>
                        ))}
                    </View>
                </>
            )}

            <View style={[s.card, { marginTop: 16, marginBottom: 32 }]}> 
                <View style={s.row}> 
                    <Text style={s.cardTitle}>History</Text>
                    <TouchableOpacity onPress={() => void loadHistory()} style={s.refreshBtn}>
                        <Text style={s.refreshText}>{historyLoading ? 'Refreshing...' : 'Refresh'}</Text>
                    </TouchableOpacity>
                </View>
                {history.length === 0 ? (
                    <Text style={s.meta}>No transcript checked yet.</Text>
                ) : history.map((h) => (
                    <View key={h.id} style={s.historyRow}>
                        <View style={{ flex: 1 }}>
                            <Text style={s.historyTop}>{(h.created_at || '').slice(0, 10)} · {h.program}</Text>
                            <Text style={s.historyBottom}>{h.total_credits ?? '—'} credits · CGPA {h.cgpa ?? '—'}</Text>
                        </View>
                        <Text style={[s.historyStatus, { color: h.graduation_status === 'PASS' ? '#22c55e' : h.graduation_status === 'FAIL' ? '#f43f5e' : '#a78bfa' }]}>{h.graduation_status || 'PENDING'}</Text>
                    </View>
                ))}
            </View>
        </ScrollView>
    )
}

const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#0d0f14' },
    headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
    headerTitle: { color: '#f8fafc', fontSize: 38, fontWeight: '700' },
    userText: { color: '#93a4bb', marginBottom: 14, fontSize: 12 },
    logoutBtn: { borderWidth: 1, borderColor: '#3a4458', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: '#111827' },
    logoutText: { color: '#e2e8f0', fontWeight: '700' },
    label: { color: '#8b92b1', fontWeight: '600', fontSize: 13, textTransform: 'uppercase', marginBottom: 10 },
    inlineRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 14 },
    chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 100, borderWidth: 1, borderColor: '#2a2f42', marginRight: 8, marginBottom: 8 },
    chipActive: { backgroundColor: '#6366f1', borderColor: '#6366f1' },
    chipText: { color: '#8b92b1', fontWeight: '600' },
    chipTextActive: { color: '#fff' },
    uploadBtn: { backgroundColor: '#6366f1', borderRadius: 12, padding: 20, alignItems: 'center', marginBottom: 20 },
    uploadBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
    card: { backgroundColor: '#161a23', borderRadius: 12, padding: 16, borderWidth: 1, borderColor: '#2a2f42' },
    row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
    cardTitle: { color: '#e8eaf3', fontWeight: '700', fontSize: 16, marginBottom: 8 },
    tableRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 7, borderBottomWidth: 1, borderBottomColor: '#263142' },
    tableKey: { color: '#94a3b8', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.7 },
    tableVal: { color: '#e2e8f0', fontWeight: '700' },
    warnText: { color: '#f59e0b', marginTop: 10, fontSize: 12 },
    banner: { marginTop: 12, marginBottom: 12, backgroundColor: '#111827', borderRadius: 12, padding: 16, borderWidth: 1, borderColor: '#2a2f42', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    bannerTitle: { fontSize: 40, fontWeight: '700' },
    bannerCgpa: { fontSize: 44, color: '#f8fafc', fontWeight: '700' },
    bannerSub: { color: '#94a3b8' },
    meta: { color: '#8b92b1', fontSize: 13 },
    missingRow: { marginTop: 10, borderWidth: 1, borderColor: '#2b3343', borderRadius: 9, paddingHorizontal: 10, paddingVertical: 8 },
    missingText: { color: '#cbd5e1', fontSize: 13 },
    refreshBtn: { borderWidth: 1, borderColor: '#475569', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#0f172a' },
    refreshText: { color: '#e2e8f0', fontWeight: '700', fontSize: 12 },
    historyRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#263142' },
    historyTop: { color: '#e2e8f0', fontWeight: '600' },
    historyBottom: { color: '#94a3b8', fontSize: 12 },
    historyStatus: { fontWeight: '700', textTransform: 'uppercase' },
})
