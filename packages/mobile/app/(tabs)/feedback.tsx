import { useState } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, TextInput, ScrollView, ActivityIndicator, Alert } from 'react-native'
import { useRouter } from 'expo-router'
import { supabase, SUPABASE_CONFIG_ERROR } from '../../lib/supabase'

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? ''
const CATEGORIES = ['Mobile App', 'Web App', 'CLI Tool', 'MCP Server', 'Other']
const FEATURES = ['Transcript Scan', 'CSV Audit', 'History View', 'Report View', 'Login/Auth', 'Other']

export default function FeedbackScreen() {
    const router = useRouter()
    const [rating, setRating] = useState(0)
    const [category, setCategory] = useState('Mobile App')
    const [featureUsed, setFeatureUsed] = useState('Transcript Scan')
    const [improvements, setImprovements] = useState('')
    const [freeform, setFreeform] = useState('')
    const [loading, setLoading] = useState(false)
    const [submitted, setSubmitted] = useState(false)

    async function submit() {
        if (!supabase) {
            Alert.alert('Configuration Error', SUPABASE_CONFIG_ERROR ?? 'Supabase is not configured')
            return
        }
        if (rating === 0) {
            Alert.alert('Please select a rating')
            return
        }
        setLoading(true)
        
        try {
            const { data: { session } } = await supabase.auth.getSession()
            const token = session?.access_token
            if (!token) throw new Error('Not authenticated')
            if (!API_URL) throw new Error('API URL not set')

            const res = await fetch(`${API_URL}/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    rating,
                    category,
                    feature_used: featureUsed,
                    improvements: improvements || null,
                    freeform: freeform || null,
                    audit_id: null,
                }),
            })

            if (!res.ok) throw new Error('Failed to submit feedback')
            setSubmitted(true)
        } catch (e: unknown) {
            Alert.alert('Error', e instanceof Error ? e.message : String(e))
        } finally {
            setLoading(false)
        }
    }

    if (submitted) {
        return (
            <View style={s.container}>
                <View style={s.successCard}>
                    <Text style={s.successIcon}>✓</Text>
                    <Text style={s.successTitle}>Thank you!</Text>
                    <Text style={s.successText}>Your feedback helps us improve.</Text>
                    <TouchableOpacity style={s.submitBtn} onPress={() => { setSubmitted(false); setRating(0); setImprovements(''); setFreeform(''); }}>
                        <Text style={s.submitBtnText}>Submit Another</Text>
                    </TouchableOpacity>
                </View>
            </View>
        )
    }

    return (
        <ScrollView style={s.container} contentContainerStyle={{ padding: 16 }}>
            <Text style={s.section}>How would you rate your experience?</Text>
            <View style={s.ratingRow}>
                {[1, 2, 3, 4, 5].map(n => (
                    <TouchableOpacity key={n} onPress={() => setRating(n)} style={s.star}>
                        <Text style={[s.starText, rating >= n && s.starActive]}>{rating >= n ? '★' : '☆'}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            <Text style={s.section}>What did you use?</Text>
            <View style={s.chipRow}>
                {CATEGORIES.map(c => (
                    <TouchableOpacity key={c} style={[s.chip, category === c && s.chipActive]} onPress={() => setCategory(c)}>
                        <Text style={[s.chipText, category === c && s.chipTextActive]}>{c}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            <Text style={s.section}>Which feature?</Text>
            <View style={s.chipRow}>
                {FEATURES.map(f => (
                    <TouchableOpacity key={f} style={[s.chip, featureUsed === f && s.chipActive]} onPress={() => setFeatureUsed(f)}>
                        <Text style={[s.chipText, featureUsed === f && s.chipTextActive]}>{f}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            <Text style={s.section}>What could be improved? (optional)</Text>
            <TextInput style={s.input} value={improvements} onChangeText={setImprovements} placeholder="Select multiple options..." placeholderTextColor="#6b7280" multiline numberOfLines={3} />

            <Text style={s.section}>Any other feedback? (freeform)</Text>
            <TextInput style={[s.input, s.inputLarge]} value={freeform} onChangeText={setFreeform} placeholder="Write anything you want..." placeholderTextColor="#6b7280" multiline numberOfLines={5} />

            <TouchableOpacity style={[s.submitBtn, loading && s.submitBtnDisabled]} onPress={submit} disabled={loading}>
                {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.submitBtnText}>Submit Feedback</Text>}
            </TouchableOpacity>
        </ScrollView>
    )
}

const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#0d0f14' },
    section: { color: '#9ca3af', fontWeight: '600', fontSize: 13, textTransform: 'uppercase', marginTop: 16, marginBottom: 8 },
    ratingRow: { flexDirection: 'row', gap: 8 },
    star: { padding: 8 },
    starText: { fontSize: 32, color: '#4b5563' },
    starActive: { color: '#fbbf24' },
    chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 100, borderWidth: 1, borderColor: '#2a2f42' },
    chipActive: { backgroundColor: '#6366f1', borderColor: '#6366f1' },
    chipText: { color: '#8b92b1', fontWeight: '600', fontSize: 13 },
    chipTextActive: { color: '#fff' },
    input: { backgroundColor: '#161a23', borderRadius: 10, padding: 14, color: '#e8eaf3', borderWidth: 1, borderColor: '#2a2f42', fontSize: 14 },
    inputLarge: { minHeight: 100, textAlignVertical: 'top' },
    submitBtn: { backgroundColor: '#6366f1', borderRadius: 12, padding: 16, alignItems: 'center', marginTop: 24, marginBottom: 40 },
    submitBtnDisabled: { opacity: 0.6 },
    submitBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
    successCard: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
    successIcon: { fontSize: 64, color: '#22c55e', marginBottom: 16 },
    successTitle: { color: '#e8eaf3', fontWeight: '700', fontSize: 24, marginBottom: 8 },
    successText: { color: '#8b92b1', fontSize: 15, textAlign: 'center' },
})
