import { ActivityIndicator, View } from 'react-native'
import { Redirect, Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useAuthSession } from '../../lib/auth'

export default function TabLayout() {
    const { session, loading } = useAuthSession()

    if (loading) {
        return (
            <View style={{ flex: 1, backgroundColor: '#0d0f14', alignItems: 'center', justifyContent: 'center' }}>
                <ActivityIndicator color="#6366f1" />
            </View>
        )
    }

    if (!session) {
        return <Redirect href={'/login' as never} />
    }

    return (
        <Tabs
            screenOptions={{
                tabBarStyle: { backgroundColor: '#161a23', borderTopColor: '#2a2f42' },
                tabBarActiveTintColor: '#6366f1',
                tabBarInactiveTintColor: '#8b92b1',
                headerStyle: { backgroundColor: '#0d0f14' },
                headerTintColor: '#e8eaf3',
            }}
        >
            <Tabs.Screen
                name="scan"
                options={{
                    title: 'Audit',
                    tabBarIcon: ({ color, size }) => <Ionicons name="scan-outline" size={size} color={color} />,
                }}
            />
            <Tabs.Screen
                name="index"
                options={{
                    href: null,
                }}
            />
            <Tabs.Screen
                name="report"
                options={{
                    href: null,
                }}
            />
            <Tabs.Screen name="feedback" options={{ href: null }} />
        </Tabs>
    )
}
