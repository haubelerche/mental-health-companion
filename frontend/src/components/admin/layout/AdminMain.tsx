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
            // Chỉ hiện modal nếu bị 401 khi đang gọi các API admin
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
