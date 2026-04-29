import { Outlet } from "react-router-dom"
import AdminSidebar from "./AdminSidebar"

const AdminMain = () => {
    return (
        <div className="flex h-screen overflow-hidden bg-gradient-to-b from-serene-secondary/20 to-white">
            <AdminSidebar />
            <div className="flex-1 overflow-y-auto p-6">
                <Outlet />
            </div>
        </div>
    )
}

export default AdminMain
