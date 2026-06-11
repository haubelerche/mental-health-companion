/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect } from "react"
import { Outlet, useNavigate } from "react-router-dom"
import AdminSidebar from "./AdminSidebar"
import { HTTP_UNAUTHORIZED_EVENT } from "../../../api/httpClient"
import { ROUTE_PATHS } from "../../../routes/paths"
import './AdminLayout.css'

const AdminMain = () => {
    const navigate = useNavigate()

    useEffect(() => {
        const handleUnauthorized = (e: any) => {
            const detail = e.detail as { path: string; status: number }

            if (window.location.pathname.includes('/admin/login')) {
                return
            }

            if (!detail.path.includes('/admin')) {
                return
            }

            // Ignore 401s that arrive within 5 s of a fresh login (cookie propagation race).
            const loginTs = Number(sessionStorage.getItem('admin_login_ts') || 0)
            if (Date.now() - loginTs < 5000) {
                return
            }

            // Session genuinely expired — clear state and redirect to login.
            sessionStorage.removeItem('admin_authenticated')
            sessionStorage.removeItem('admin_login_ts')
            navigate(ROUTE_PATHS.adminLogin, { replace: true })
        }

        window.addEventListener(HTTP_UNAUTHORIZED_EVENT, handleUnauthorized)
        return () => window.removeEventListener(HTTP_UNAUTHORIZED_EVENT, handleUnauthorized)
    }, [navigate])

    return (
        <div className="admin-layout">
            <AdminSidebar />
            <main className="admin-main-content">
                <Outlet />
            </main>
        </div>
    )
}

export default AdminMain
