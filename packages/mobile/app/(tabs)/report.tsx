import { useEffect, useState } from 'react'
import { View, Text, ScrollView, StyleSheet, ActivityIndicator } from 'react-native'

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? ''

interface FeedbackData {
    rating: number
    category: string
    feature_used: string
    improvements: string | null
    freeform: string | null
    created_at: string
}

export default function ReportScreen() {
    const [feedback, setFeedback] = useState<FeedbackData[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function loadFeedback() {
            try {
                const res = await fetch(`${API_URL}/feedback/all?limit=100`)
                if (!res.ok) throw new Error('Failed to load')
                const data = await res.json()
                setFeedback(Array.isArray(data) ? data : [])
            } catch (e) {
                console.error(e)
            } finally {
                setLoading(false)
            }
        }
        loadFeedback()
    }, [])

    if (loading) {
        return (
            <View style={s.container}>
                <ActivityIndicator color="#6366f1" style={{ marginTop: 40 }} />
            </View>
        )
    }

    if (feedback.length === 0) {
        return (
            <View style={s.container}>
                <View style={s.empty}>
                    <Text style={s.emptyIcon}>📊</Text>
                    <Text style={s.emptyText}>No feedback yet. Check back later.</Text>
                </View>
            </View>
        )
    }

    const ratings = [1, 2, 3, 4, 5]
    const ratingCounts = ratings.map(r => feedback.filter(f => f.rating === r).length)
    const maxRating = Math.max(...ratingCounts, 1)

    const categories = [...new Set(feedback.map(f => f.category))]
    const categoryCounts = categories.map(c => feedback.filter(f => f.category === c).length)
    const maxCat = Math.max(...categoryCounts, 1)

    const features = [...new Set(feedback.map(f => f.feature_used))]
    const featureCounts = features.map(feature => feedback.filter(f => f.feature_used === feature).length)
    const maxFeat = Math.max(...featureCounts, 1)

    const avgRating = (feedback.reduce((sum, f) => sum + f.rating, 0) / feedback.length).toFixed(1)

    return (
        <ScrollView style={s.container} contentContainerStyle={{ padding: 16 }}>
            <Text style={s.title}>Feedback Analysis</Text>
            <Text style={s.subtitle}>{feedback.length} total responses</Text>

            <View style={s.statsRow}>
                <View style={s.statCard}>
                    <Text style={s.statValue}>{avgRating}</Text>
                    <Text style={s.statLabel}>Avg Rating</Text>
                </View>
                <View style={s.statCard}>
                    <Text style={s.statValue}>{feedback.filter(f => f.rating >= 4).length}</Text>
                    <Text style={s.statLabel}>4+ Stars</Text>
                </View>
                <View style={s.statCard}>
                    <Text style={s.statValue}>{feedback.filter(f => f.freeform && f.freeform.length > 20).length}</Text>
                    <Text style={s.statLabel}>With Comments</Text>
                </View>
            </View>

            <View style={s.chartCard}>
                <Text style={s.chartTitle}>Rating Distribution</Text>
                {ratings.map((r, i) => (
                    <View key={r} style={s.barRow}>
                        <Text style={s.barLabel}>{r} ★</Text>
                        <View style={s.barContainer}>
                            <View style={[s.bar, { width: `${(ratingCounts[i] / maxRating) * 100}%` }]} />
                        </View>
                        <Text style={s.barValue}>{ratingCounts[i]}</Text>
                    </View>
                ))}
            </View>

            <View style={s.chartCard}>
                <Text style={s.chartTitle}>By Category</Text>
                {categories.map((c, i) => (
                    <View key={c} style={s.barRow}>
                        <Text style={s.barLabel}>{c}</Text>
                        <View style={s.barContainer}>
                            <View style={[s.bar, { width: `${(categoryCounts[i] / maxCat) * 100}%`, backgroundColor: '#8b5cf6' }]} />
                        </View>
                        <Text style={s.barValue}>{categoryCounts[i]}</Text>
                    </View>
                ))}
            </View>

            <View style={s.chartCard}>
                <Text style={s.chartTitle}>Features Used</Text>
                {features.map((f, i) => (
                    <View key={f} style={s.barRow}>
                        <Text style={s.barLabel}>{f}</Text>
                        <View style={s.barContainer}>
                            <View style={[s.bar, { width: `${(featureCounts[i] / maxFeat) * 100}%`, backgroundColor: '#10b981' }]} />
                        </View>
                        <Text style={s.barValue}>{featureCounts[i]}</Text>
                    </View>
                ))}
            </View>

            {feedback.filter(f => f.freeform).length > 0 && (
                <View style={s.commentsCard}>
                    <Text style={s.chartTitle}>Recent Comments</Text>
                    {feedback.filter(f => f.freeform).slice(0, 5).map((f, i) => (
                        <View key={i} style={s.comment}>
                            <Text style={s.commentText}>"{f.freeform}"</Text>
                            <Text style={s.commentMeta}>{f.category} · {f.rating}★</Text>
                        </View>
                    ))}
                </View>
            )}
        </ScrollView>
    )
}

const s = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#0d0f14' },
    title: { color: '#e8eaf3', fontWeight: '700', fontSize: 24, marginBottom: 4 },
    subtitle: { color: '#8b92b1', fontSize: 14, marginBottom: 20 },
    statsRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
    statCard: { flex: 1, backgroundColor: '#161a23', borderRadius: 12, padding: 16, alignItems: 'center', borderWidth: 1, borderColor: '#2a2f42' },
    statValue: { color: '#6366f1', fontWeight: '700', fontSize: 28 },
    statLabel: { color: '#8b92b1', fontSize: 12, marginTop: 4 },
    chartCard: { backgroundColor: '#161a23', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#2a2f42' },
    chartTitle: { color: '#e8eaf3', fontWeight: '700', fontSize: 16, marginBottom: 12 },
    barRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
    barLabel: { width: 90, color: '#9ca3af', fontSize: 13 },
    barContainer: { flex: 1, height: 20, backgroundColor: '#2a2f42', borderRadius: 4, overflow: 'hidden' },
    bar: { height: '100%', backgroundColor: '#6366f1', borderRadius: 4 },
    barValue: { width: 30, textAlign: 'right', color: '#9ca3af', fontSize: 13 },
    commentsCard: { backgroundColor: '#161a23', borderRadius: 12, padding: 16, marginBottom: 40, borderWidth: 1, borderColor: '#2a2f42' },
    comment: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#2a2f42' },
    commentText: { color: '#d1d5db', fontSize: 14, fontStyle: 'italic' },
    commentMeta: { color: '#6b7280', fontSize: 12, marginTop: 6 },
    empty: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
    emptyIcon: { fontSize: 48 },
    emptyText: { color: '#8b92b1', fontSize: 15, textAlign: 'center' },
})
