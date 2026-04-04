import { useEffect, useState } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { useRouter } from 'expo-router'
import { supabase } from '../../lib/supabase'

interface Scan {
    id: string
    created_at: string
    program: string
    total_credits: number
    cgpa: number
    graduation_status: string
}

export default function DashboardScreen() {
    const router = useRouter()
    const [scans, setScans] = useState<Scan[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        supabase
            .from('transcript_scans')
            .select('id, created_at, program, total_credits, cgpa, graduation_status')
            .order('created_at', { ascending: false })
            .limit(50)
            .then(({ data }) => { setScans(data ?? []); setLoading(false) })
    }, [])

    const statusColor = (s: string) =>
        s === 'PASS' ? '#22c55e' : s === 'FAIL' ? '#f43f5e' : '#a78bfa'

    return (
        <View style={s.container}>
            <TouchableOpacity style={s.fab} onPress={() => router.push('/(tabs)/scan')}>
                <Text style={s.fabText}>+ New Scan</Text>
            </TouchableOpacity>

            {loading ? (
                <ActivityIndicator color="#6366f1" style={{ marginTop: 40 }} />
            ) : scans.length === 0 ? (
                <View style={s.empty}>
                    <Text style={s.emptyIcon}>📄</Text>
                    <Text style={s.emptyText}>No scans yet. Tap + New Scan to begin.</Text>
                </View>
            ) : (
                <FlatList
                    data={scans}
                    keyExtractor={i => i.id}
                    contentContainerStyle={{ padding: 16 }}
                    renderItem={({ item }) => (
                        <TouchableOpacity style={s.card} onPress={() => router.push({ pathname: '/(tabs)/report', params: { id: item.id } })}>
                            <View style={s.cardRow}>
                                <Text style={s.program}>{item.program ?? '—'}</Text>
                                <View style={[s.badge, { backgroundColor: statusColor(item.graduation_status) + '22' }]}>
                                    <Text style={[s.badgeText, { color: statusColor(item.graduation_status) }]}>{item.graduation_status}</Text>
                                </View>
                            </View>
                            <Text style={s.meta}>{new Date(item.created_at).toLocaleDateString()} · {item.total_credits} credits · CGPA {item.cgpa}</Text>
                        </TouchableOpacity>
                    )}
                />
            )}
        </View>
    )
}

const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#0d0f14' },
    fab: { margin: 16, backgroundColor: '#6366f1', borderRadius: 10, padding: 14, alignItems: 'center' },
    fabText: { color: '#fff', fontWeight: '700', fontSize: 15 },
    empty: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
    emptyIcon: { fontSize: 48 },
    emptyText: { color: '#8b92b1', fontSize: 15, textAlign: 'center' },
    card: { backgroundColor: '#161a23', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#2a2f42' },
    cardRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
    program: { color: '#e8eaf3', fontWeight: '700', fontSize: 16 },
    badge: { borderRadius: 100, paddingHorizontal: 10, paddingVertical: 3 },
    badgeText: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase' },
    meta: { color: '#8b92b1', fontSize: 13 },
})
