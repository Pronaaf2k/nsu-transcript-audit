import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

export default function TabLayout() {
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
