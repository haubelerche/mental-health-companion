import { Outlet } from "react-router-dom"

const AdminMain = () => {
    return (
        <div className="h-screen overflow-hidden flex">
            {/* sidebar */}
            <div className="w-64">Sidebar</div>

            {/* main */}
            <div className="flex-1 flex flex-col">
                <Outlet />
            </div>
        </div>
    )
}

export default AdminMain