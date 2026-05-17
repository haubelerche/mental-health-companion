/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react"
import { Outlet } from "react-router-dom"
import AdminSidebar from "./AdminSidebar"
import AdminReAuthModal from "./AdminReAuthModal"
import { HTTP_UNAUTHORIZED_EVENT } from "../../../api/httpClient"
import './AdminLayout.css'

const AdminMain = () => {
    const [showReAuth, setShowReAuth] = useState(false)

    useEffect(() => {
        const handleUnauthorized = (e: any) => {
            const detail = e.detail as { path: string; status: number }

            // Nếu đang ở trang login rồi thì không hiện modal nữa
            if (window.location.pathname.includes('/admin/login')) {
                return
            }

            // Show reauth modal on any admin 401/403. The admin_access_token cookie
            // expires after ADMIN_TOKEN_TTL_SECONDS regardless of sessionStorage state,
            // so we must not suppress the modal based on that flag.
            if (detail.path.includes('/admin')) {
                setShowReAuth(true)
            }
        }

        window.addEventListener(HTTP_UNAUTHORIZED_EVENT, handleUnauthorized)
        return () => window.removeEventListener(HTTP_UNAUTHORIZED_EVENT, handleUnauthorized)
    }, [])

    return (
        <div className="admin-layout">
            <AdminSidebar />
            <main className="admin-main-content">
                <Outlet />
            </main>

            {showReAuth && (
                <AdminReAuthModal 
                    onSuccess={() => {
                        setShowReAuth(false)
                        // Tải lại trang hoặc reload dữ liệu nếu cần, 
                        // nhưng thường re-login xong thì request tiếp theo sẽ chạy được.
                        window.location.reload() 
                    }} 
                />
            )}
        </div>
    )
}

export default AdminMain
