import { Navigate, Route, Routes, Outlet } from 'react-router-dom'
import type { ReactElement } from 'react'
import Login from '../components/auth/Login.tsx'
import OAuthCallback from '../components/auth/OAuthCallback.tsx'
import Register from '../components/auth/Register.tsx'
import Chat from '../components/pages/chat/Chat.tsx'
import Main from '../components/layout/Main.tsx'
import Support from '../components/pages/Support.tsx'

import Landing from '../components/pages/landing/Landing.tsx'
import PrivacyPolicy from '../components/pages/PrivacyPolicy.tsx'
import DeleteDataInstructions from '../components/pages/DeleteDataInstructions.tsx'
import Reflect from '../components/pages/reflect/Reflect.tsx'
import Resources from '../components/pages/resource/Resources.tsx'
import Nutrition from '../components/nutrition/Nutrition.tsx'
import { CheckinFlow } from '../components/common/CheckinFlow.tsx'
import { SafetyCheck } from '../components/pages/SafetyCheck'
import { ScreeningFlow } from '../components/pages/ScreeningFlow'
import { ResultsPage } from '../components/pages/ResultsPage'
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
import AdminAutomation from '../components/admin/AdminAutomation'
import AdminSystemTrace from '../components/admin/AdminSystemTrace'
import Home from '../components/pages/Home.tsx'
import RewardsPage from '../components/pages/rewards/RewardsPage.tsx'
import { ExercisesPage } from '@/components/pages/exercises/ExercisesPage.tsx'
import NotificationsRouteBridge from '../components/pages/notifications/NotificationsRouteBridge.tsx'
import Loading from '@/components/ui/Loading.tsx'

function RequireAuth({ children }: { children: ReactElement }) {
    const { user, isLoading } = useAuth()
    if (isLoading) {
        return <Loading />
    }
    if (!user) {
        return <Navigate to={ROUTE_PATHS.login} replace />
    }
    return children
}

function RequireAdminAuth({ children }: { children: ReactElement }) {
    if (!sessionStorage.getItem('admin_authenticated')) {
        return <Navigate to={ROUTE_PATHS.adminLogin} replace />
    }
    return children
}

function RequireGuest({ children }: { children: ReactElement }) {
    const { user, isLoading } = useAuth()
    if (isLoading) {
        return <Loading />
    }
    if (user) {
        return <Navigate to={ROUTE_PATHS.home} replace />
    }
    return children
}

function RequireOnboarding({ children }: { children: ReactElement }) {
    const { user, isLoading } = useAuth()
    if (isLoading) {
        return <Loading />
    }
    if (user && !user.onboardingCompleted) {
        return <Navigate to={ROUTE_PATHS.onboarding} replace />
    }
    return children
}

function RequireUserOrGuest({ children }: { children: ReactElement }) {
    const { user, guestSession, isLoading } = useAuth()
    
    if (isLoading) {
        return <Loading />
    }
    
    // If logged in user, allowed
    if (user) {
        return children
    }
    
    // Check guest session from context first
    if (guestSession && Date.now() >= guestSession.expiresAt) {
        return <Navigate to={ROUTE_PATHS.login} replace />
    }
    
    // Fallback to persisted expiration time in localStorage
    const expiresAtStr = localStorage.getItem('serene_guest_session_expires_at')
    if (expiresAtStr) {
        const expiresAt = Number(expiresAtStr)
        if (Date.now() >= expiresAt) {
            return <Navigate to={ROUTE_PATHS.login} replace />
        }
    }
    
    // If no session or valid session, allow access
    // This allows Chat.tsx to load and create the session!
    return children
}

export default function AppRoutes() {
    return (
        <Routes>
            {/* admin */}
            <Route path={ROUTE_PATHS.adminLogin} element={<AdminLogin />} />
            <Route path={ROUTE_PATHS.admin} element={<RequireAdminAuth><AdminMain /></RequireAdminAuth>}>
                <Route index element={<Navigate to={ROUTE_PATHS.adminDashboard} replace />} />
                <Route path="dashboard" element={<AdminDashboard />} />
                <Route path="crisis-logs" element={<AdminCrisisLogs />} />
                <Route path="resources" element={<AdminResources />} />
                <Route path="users" element={<AdminUsers />} />
                <Route path="letters" element={<AdminLetters />} />
                <Route path="audit-logs" element={<AdminAuditLogs />} />
                <Route path="notifications" element={<AdminNotifications />} />
                <Route path="analytics" element={<AdminAnalytics />} />
                <Route path="automation" element={<AdminAutomation />} />
                <Route path="system-trace" element={<AdminSystemTrace />} />
            </Route>



            {/* user */}
            <Route path={ROUTE_PATHS.root} element={<Navigate to={ROUTE_PATHS.landing} replace />} />
            <Route path={ROUTE_PATHS.login} element={<RequireGuest><Login /></RequireGuest>} />
            <Route path={ROUTE_PATHS.oauthCallback} element={<OAuthCallback />} />
            <Route path={ROUTE_PATHS.register} element={<RequireGuest><Register /></RequireGuest>} />
            <Route path={ROUTE_PATHS.forget} element={<RequireGuest><Forget /></RequireGuest>} />
            <Route path={ROUTE_PATHS.landing} element={<Landing />} />
            <Route path={ROUTE_PATHS.privacy} element={<PrivacyPolicy />} />
            <Route path={ROUTE_PATHS.deleteData} element={<DeleteDataInstructions />} />
            <Route path="/terms" element={<Navigate to={ROUTE_PATHS.privacy} replace />} />
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
             
                        <RequireOnboarding>
                            <Main />
                        </RequireOnboarding>
                
                }
            >
                {/* Routes that require full authentication */}
                <Route element={<RequireAuth><Outlet /></RequireAuth>}>
                    <Route index element={<Home />} />
                    <Route path={ROUTE_PATHS.reflect} element={<Reflect />} />
                    <Route path={ROUTE_PATHS.resources} element={<Resources />} />
                    <Route path={ROUTE_PATHS.nutrition} element={<Nutrition />} />
                    <Route path={ROUTE_PATHS.support} element={<Support />} />
                    <Route path={ROUTE_PATHS.profile} element={<Profile />} />
                    <Route path={ROUTE_PATHS.setting} element={<Setting />} />
                    <Route path={ROUTE_PATHS.safetyCheck} element={<SafetyCheck />} />
                    <Route path={ROUTE_PATHS.checkin} element={<CheckinFlow />} />
                    <Route path={ROUTE_PATHS.screening} element={<ScreeningFlow />} />
                    <Route path={ROUTE_PATHS.results} element={<ResultsPage />} />
                    <Route path={ROUTE_PATHS.exercises} element={<ExercisesPage />} />
                    <Route path={ROUTE_PATHS.bamboo} element={<LetterPage />} />
                    <Route path={ROUTE_PATHS.rewards} element={<RewardsPage />} />
                    <Route path={ROUTE_PATHS.notifications} element={<NotificationsRouteBridge />} />
                </Route>

                {/* Routes that allow guests (or authenticated users) */}
                <Route 
                    path={ROUTE_PATHS.chat} 
                    element={
                        <RequireUserOrGuest>
                            <Chat />
                        </RequireUserOrGuest>
                    } 
                />
            </Route>

            <Route path="*" element={<Navigate to={ROUTE_PATHS.landing} replace />} />
        </Routes>
    )
}
