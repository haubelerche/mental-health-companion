import { Navigate, Route, Routes } from 'react-router-dom'
import Login from '../components/auth/Login.tsx'
import Register from '../components/auth/Register.tsx'
import Chat from '../components/chat/Chat.tsx'
import Main from '../components/layout/Main.tsx'
import Connect from '../components/pages/Connect.tsx'
import Home from '../components/pages/Home.tsx'
import Landing from '../components/pages/Landing.tsx'
import Reflect from '../components/pages/Reflect.tsx'
import Resources from '../components/pages/Resources.tsx'
import { ROUTE_PATHS } from './paths'

export default function AppRoutes() {
    return (
        <Routes>
            <Route path={ROUTE_PATHS.root} element={<Navigate to={ROUTE_PATHS.landing} replace />} />
            <Route path={ROUTE_PATHS.login} element={<Login />} />
            <Route path={ROUTE_PATHS.register} element={<Register />} />
            <Route path={ROUTE_PATHS.landing} element={<Landing />} />

            <Route path={ROUTE_PATHS.home} element={<Main />}>
                <Route index element={<Home />} />
                <Route path="chat" element={<Chat />} />
                <Route path="reflect" element={<Reflect />} />
                <Route path="resources" element={<Resources />} />
                <Route path="connect" element={<Connect />} />
            </Route>

            <Route path="*" element={<Navigate to={ROUTE_PATHS.landing} replace />} />
        </Routes>
    )
}
