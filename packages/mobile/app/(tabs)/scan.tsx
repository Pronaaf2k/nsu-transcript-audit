import { useState } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, ScrollView } from 'react-native'
import * as DocumentPicker from 'expo-document-picker'
import { supabase } from '../../lib/supabase'

const PROGRAMS = ['CSE', 'BBA', 'ETE', 'ENV', 'ENG', 'ECO']
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? ''

export default function ScanScreen() {
    const [program, setProgram] = useState('CSE')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<Record<string, unknown> | null>(null)

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
            if (file.name?.endsWith('.csv') || file.mimeType?.includes('csv')) {
                const resp = await fetch(file.uri)
                const csv_text = await resp.text()
                res = await fetch(`${API_URL}/audit/run_csv`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ csv_text, program }),
                })
            } else {
                const form = new FormData()
                form.append('program', program)
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
        } catch (e: unknown) {
            Alert.alert('Error', e instanceof Error ? e.message : String(e))
        } finally {
            setLoading(false)
        }
    }

    const status = (result as { graduation_status?: string })?.graduation_status
    const statusColor = status === 'PASS' ? '#22c55e' : status === 'FAIL' ? '#f43f5e' : '#a78bfa'

    return (
        <ScrollView style={s.container} contentContainerStyle={{ padding: 16 }}>
            <Text style={s.label}>Program</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 20 }}>
                {PROGRAMS.map(p => (
                    <TouchableOpacity key={p} style={[s.chip, program === p && s.chipActive]} onPress={() => setProgram(p)}>
                        <Text style={[s.chipText, program === p && s.chipTextActive]}>{p}</Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            <TouchableOpacity style={s.uploadBtn} onPress={pickAndScan} disabled={loading}>
                {loading
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={s.uploadBtnText}>📄  Select Transcript (PDF / Image / CSV)</Text>
                }
            </TouchableOpacity>

            {result && (
                <View style={s.card}>
                    <View style={s.row}>
                        <Text style={s.cardTitle}>Audit Result</Text>
                        <View style={[s.badge, { backgroundColor: statusColor + '22' }]}>
                            <Text style={[s.badgeText, { color: statusColor }]}>{status}</Text>
                        </View>
                    </View>
                    <Text style={s.meta}>
                        Credits: {(result as { total_credits?: number }).total_credits ?? '—'}  ·  CGPA: {(result as { cgpa?: number }).cgpa ?? '—'}
                    </Text>
                </View>
            )}
        </ScrollView>
    )
}

const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#0d0f14' },
    label: { color: '#8b92b1', fontWeight: '600', fontSize: 13, textTransform: 'uppercase', marginBottom: 10 },
    chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 100, borderWidth: 1, borderColor: '#2a2f42', marginRight: 8 },
    chipActive: { backgroundColor: '#6366f1', borderColor: '#6366f1' },
    chipText: { color: '#8b92b1', fontWeight: '600' },
    chipTextActive: { color: '#fff' },
    uploadBtn: { backgroundColor: '#6366f1', borderRadius: 12, padding: 20, alignItems: 'center', marginBottom: 20 },
    uploadBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
    card: { backgroundColor: '#161a23', borderRadius: 12, padding: 16, borderWidth: 1, borderColor: '#2a2f42' },
    row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
    cardTitle: { color: '#e8eaf3', fontWeight: '700', fontSize: 16 },
    badge: { borderRadius: 100, paddingHorizontal: 10, paddingVertical: 3 },
    badgeText: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase' },
    meta: { color: '#8b92b1', fontSize: 13 },
})
