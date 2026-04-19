import { Navigate, Route, Routes } from 'react-router-dom'
import Login from '../components/auth/Login'
import Register from '../components/auth/Register'
import Chat from '../components/chat/Chat'
import Main from '../components/layout/Main'
import Home from '../components/pages/Home'
import Landing from '../components/pages/Landing'
import { ROUTE_PATHS } from './paths'

export default function AppRoutes() {
    return (
        <Routes>
            <Route path={ROUTE_PATHS.root} element={<Navigate to={ROUTE_PATHS.landing} replace />} />
            <Route path={ROUTE_PATHS.login} element={<Login />} />
            <Route path={ROUTE_PATHS.register} element={<Register />} />
            <Route path={ROUTE_PATHS.landing} element={<Landing />} />

            <Route path={ROUTE_PATHS.app} element={<Main />}>
                <Route index element={<Home />} />
                <Route path="chat" element={<Chat />} />
            </Route>

            <Route path="*" element={<Navigate to={ROUTE_PATHS.landing} replace />} />
        </Routes>
    )
}
