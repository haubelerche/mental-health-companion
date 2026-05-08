import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactElement } from 'react'
import Login from '../components/auth/Login.tsx'
import OAuthCallback from '../components/auth/OAuthCallback.tsx'
import Register from '../components/auth/Register.tsx'
import Chat from '../components/chat/Chat.tsx'
import Main from '../components/layout/Main.tsx'
import Support from '../components/pages/Support.tsx'

import Landing from '../components/pages/landing/Landing.tsx'
import Reflect from '../components/pages/Reflect.tsx'
import Resources from '../components/pages/resource/Resources.tsx'
import Nutrition from '../components/nutrition/Nutrition.tsx'
import { CheckinFlow } from '../components/common/CheckinFlow.tsx'
import { SafetyCheck } from '../components/pages/SafetyCheck'
import { ScreeningFlow } from '../components/pages/ScreeningFlow'
import { ResultsPage } from '../components/pages/ResultsPage'
import { ExercisesPage } from '../components/pages/ExercisesPage'
import { OnboardingFlow } from '../components/pages/onboarding/OnboardingFlow.tsx'
import LetterPage from '../components/pages/BeachMessage.tsx'
import { useAuth } from '../hooks/useAuth'
import { ROUTE_PATHS } from './paths'
import Setting from '../components/pages/Setting.tsx'
import Profile from '../components/pages/Profile.tsx'
import Forget from '../components/auth/Forget.tsx'
import AdminLogin from '../components/admin/AdminLogin.tsx'
import AdminDashboard from '../components/admin/AdminDashboard'
import AdminCrisisLogs from '../components/admin/AdminCrisisLogs'
import AdminResources from '../components/admin/AdminResources'
import AdminUsers from '../components/admin/AdminUsers'
import AdminAnalytics from '../components/admin/AdminAnalytics'
import AdminLetters from '../components/admin/AdminLetters'
import AdminAuditLogs from '../components/admin/AdminAuditLogs'
import AdminNotifications from '../components/admin/AdminNotifications.tsx'
import AdminMain from '../components/admin/layout/AdminMain.tsx'
import Home from '../components/pages/Home.tsx'
import RewardsPage from '../components/pages/RewardsPage.tsx'
import NotificationsPage from '../components/pages/Notifications.tsx'

function RequireAuth({ children }: { children: ReactElement }) {
    const { user, isLoading } = useAuth()
    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-theme-accent border-t-transparent" />
            </div>
        )
    }
    if (!user) {
        return <Navigate to={ROUTE_PATHS.login} replace />
    }
    return children
}

function RequireOnboarding({ children }: { children: ReactElement }) {
    const { user, isLoading } = useAuth()
    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-theme-accent border-t-transparent" />
            </div>
        )
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
                <Route path="users" element={<AdminUsers />} />
                <Route path="letters" element={<AdminLetters />} />
                <Route path="audit-logs" element={<AdminAuditLogs />} />
                <Route path="notifications" element={<AdminNotifications />} />
                <Route path="analytics" element={<AdminAnalytics />} />
            </Route>

            {/* user */}
            <Route path={ROUTE_PATHS.root} element={<Navigate to={ROUTE_PATHS.landing} replace />} />
            <Route path={ROUTE_PATHS.login} element={<Login />} />
            <Route path={ROUTE_PATHS.oauthCallback} element={<OAuthCallback />} />
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
                    path={ROUTE_PATHS.support}
                    element={
                        <Support />
                    }
                />
                <Route
                    path={ROUTE_PATHS.profile}
                    element={
                        <Profile />
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
                <Route
                    path={ROUTE_PATHS.rewards}
                    element={
                        <RewardsPage />
                    }
                />
                <Route
                    path={ROUTE_PATHS.notifications}
                    element={
                        <NotificationsPage />
                    }
                />
            </Route>

            <Route path="*" element={<Navigate to={ROUTE_PATHS.landing} replace />} />
        </Routes>
    )
}
