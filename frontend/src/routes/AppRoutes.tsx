import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactElement } from 'react'
import Login from '../components/auth/Login.tsx'
import Register from '../components/auth/Register.tsx'
import Chat from '../components/chat/Chat.tsx'
import Main from '../components/layout/Main.tsx'
import Connect from '../components/pages/Connect.tsx'

import Landing from '../components/pages/Landing.tsx'
import Reflect from '../components/pages/Reflect.tsx'
import Resources from '../components/pages/Resources.tsx'
import Nutrition from '../components/pages/Nutrition.tsx'
import { CheckinFlow } from '../components/pages/CheckinFlow'
import { SafetyCheck } from '../components/pages/SafetyCheck'
import { ScreeningFlow } from '../components/pages/ScreeningFlow'
import { ResultsPage } from '../components/pages/ResultsPage'
import { ExercisesPage } from '../components/pages/ExercisesPage'
import { OnboardingFlow } from '../components/pages/OnboardingFlow.tsx'
import LetterPage from '../components/pages/BeachMessage.tsx'
import { useAuth } from '../hooks/useAuth'
import { ROUTE_PATHS } from './paths'
import Setting from '../components/pages/Setting.tsx'
import Forget from '../components/auth/Forget.tsx'
import AdminLogin from '../components/admin/AdminLogin.tsx'
import AdminDashboard from '../components/admin/AdminDashboard'
import AdminCrisisLogs from '../components/admin/AdminCrisisLogs'
import AdminResources from '../components/admin/AdminResources'
import AdminMain from '../components/admin/layout/AdminMain.tsx'
import Home from '../components/pages/Home.tsx'

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

function RequireOnboarding({ children }: { children: ReactElement }) {
    const { user, isLoading } = useAuth()
    if (isLoading) {
        return null
    }
    if (user && !user.onboardingCompleted) {
        return <Navigate to={ROUTE_PATHS.onboarding} replace />
    }
    return children
}

export default function AppRoutes() {
    return (
        <Routes>
            {/* admin */}
            <Route path={ROUTE_PATHS.adminLogin} element={<AdminLogin />} />
            <Route path={ROUTE_PATHS.admin} element={<AdminMain />}>
                <Route index element={<Navigate to={ROUTE_PATHS.adminDashboard} replace />} />
                <Route path="dashboard" element={<AdminDashboard />} />
                <Route path="crisis-logs" element={<AdminCrisisLogs />} />
                <Route path="resources" element={<AdminResources />} />
            </Route>

            {/* user */}
            <Route path={ROUTE_PATHS.root} element={<Navigate to={ROUTE_PATHS.landing} replace />} />
            <Route path={ROUTE_PATHS.login} element={<Login />} />
            <Route path={ROUTE_PATHS.register} element={<Register />} />
            <Route path={ROUTE_PATHS.forget} element={<Forget />} />
            <Route path={ROUTE_PATHS.landing} element={<Landing />} />
            <Route path={ROUTE_PATHS.onboardingPolicy} element={<Navigate to={ROUTE_PATHS.onboarding} replace />} />

            <Route
                path={ROUTE_PATHS.onboarding}
                element={
                    <RequireAuth>
                        <OnboardingFlow />
                    </RequireAuth>
                }
            />

            <Route
                path={ROUTE_PATHS.home}
                element={
                    <RequireAuth>
                        <RequireOnboarding>
                            <Main />
                        </RequireOnboarding>
                    </RequireAuth>
                }
            >
                <Route
                    index
                    element={
                        <Home />
                    }
                />
                <Route path={ROUTE_PATHS.chat} element={<Chat />} />
                <Route
                    path={ROUTE_PATHS.reflect}
                    element={
                        <Reflect />
                    }
                />
                <Route
                    path={ROUTE_PATHS.resources}
                    element={
                        <Resources />
                    }
                />
                <Route
                    path={ROUTE_PATHS.nutrition}
                    element={
                        <Nutrition />
                    }
                />
                <Route
                    path={ROUTE_PATHS.connect}
                    element={
                        <Connect />
                    }
                />
                <Route
                    path={ROUTE_PATHS.setting}
                    element={
                        <Setting />
                    }
                />
                <Route
                    path={ROUTE_PATHS.safetyCheck}
                    element={
                        <SafetyCheck />
                    }
                />
                <Route
                    path={ROUTE_PATHS.checkin}
                    element={
                        <CheckinFlow />
                    }
                />
                <Route
                    path={ROUTE_PATHS.screening}
                    element={
                        <ScreeningFlow />
                    }
                />
                <Route
                    path={ROUTE_PATHS.results}
                    element={
                        <ResultsPage />
                    }
                />
                <Route
                    path={ROUTE_PATHS.exercises}
                    element={
                        <ExercisesPage />
                    }
                />
                <Route
                    path={ROUTE_PATHS.bamboo}
                    element={
                        <LetterPage />
                    }
                />
            </Route>

            <Route path="*" element={<Navigate to={ROUTE_PATHS.landing} replace />} />
        </Routes>
    )
}
