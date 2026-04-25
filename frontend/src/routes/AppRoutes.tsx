import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactElement } from 'react'
import Login from '../components/auth/Login.tsx'
import Register from '../components/auth/Register.tsx'
import { PolicyWizard } from '../components/policy/PolicyWizard'
import Chat from '../components/chat/Chat.tsx'
import Main from '../components/layout/Main.tsx'
import Connect from '../components/pages/Connect.tsx'
import { HomeToday } from '../components/pages/HomeToday'
import Landing from '../components/pages/Landing.tsx'
import Reflect from '../components/pages/Reflect.tsx'
import Resources from '../components/pages/Resources.tsx'
import { CheckinFlow } from '../components/pages/CheckinFlow'
import { SafetyCheck } from '../components/pages/SafetyCheck'
import { ScreeningFlow } from '../components/pages/ScreeningFlow'
import { ResultsPage } from '../components/pages/ResultsPage'
import { ExercisesPage } from '../components/pages/ExercisesPage'
import { useAuth } from '../hooks/useAuth'
import { ROUTE_PATHS } from './paths'
import Setting from '../components/pages/Setting.tsx'
import Forget from '../components/auth/Forget.tsx'

function RequireAuth({ children }: { children: ReactElement }) {
    const { user, isLoading } = useAuth()
    if (isLoading) {
        return null
    }
    if (!user) {
        return <Navigate to={ROUTE_PATHS.login} replace />
    }
    return children
}

export default function AppRoutes() {
    return (
        <Routes>
            <Route path={ROUTE_PATHS.root} element={<Navigate to={ROUTE_PATHS.landing} replace />} />
            <Route path={ROUTE_PATHS.login} element={<Login />} />
            <Route path={ROUTE_PATHS.register} element={<Register />} />
            <Route path={ROUTE_PATHS.forget} element={<Forget />} />
            <Route path={ROUTE_PATHS.landing} element={<Landing />} />
            <Route path={ROUTE_PATHS.onboardingPolicy} element={<PolicyWizard />} />

            <Route path={ROUTE_PATHS.home} element={<Main />}>
                <Route
                    index
                    element={
                        <RequireAuth>
                            <HomeToday />
                        </RequireAuth>
                    }
                />
                <Route path={ROUTE_PATHS.chat} element={<Chat />} />
                <Route
                    path={ROUTE_PATHS.reflect}
                    element={
                        <RequireAuth>
                            <Reflect />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.resources}
                    element={
                        <RequireAuth>
                            <Resources />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.connect}
                    element={
                        <RequireAuth>
                            <Connect />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.setting}
                    element={
                        <RequireAuth>
                            <Setting />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.safetyCheck}
                    element={
                        <RequireAuth>
                            <SafetyCheck />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.checkin}
                    element={
                        <RequireAuth>
                            <CheckinFlow />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.screening}
                    element={
                        <RequireAuth>
                            <ScreeningFlow />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.results}
                    element={
                        <RequireAuth>
                            <ResultsPage />
                        </RequireAuth>
                    }
                />
                <Route
                    path={ROUTE_PATHS.exercises}
                    element={
                        <RequireAuth>
                            <ExercisesPage />
                        </RequireAuth>
                    }
                />
            </Route>

            <Route path="*" element={<Navigate to={ROUTE_PATHS.landing} replace />} />
        </Routes>
    )
}
