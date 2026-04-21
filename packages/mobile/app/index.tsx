import { ActivityIndicator, View } from 'react-native'
import { Redirect } from 'expo-router'
import { useAuthSession } from '../lib/auth'

export default function IndexScreen() {
    const { session, loading } = useAuthSession()

    if (loading) {
        return (
            <View style={{ flex: 1, backgroundColor: '#0d0f14', alignItems: 'center', justifyContent: 'center' }}>
                <ActivityIndicator color="#6366f1" />
            </View>
        )
    }

    return <Redirect href={(session ? '/(tabs)/scan' : '/login') as never} />
}
