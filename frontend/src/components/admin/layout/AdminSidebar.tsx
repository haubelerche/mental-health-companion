import { Activity, AlertTriangle, LayoutDashboard, LogOut, Package } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { ROUTE_PATHS } from '../../../routes/paths'

const links = [
    { to: ROUTE_PATHS.adminDashboard, label: 'Dashboard', icon: LayoutDashboard },
    { to: ROUTE_PATHS.adminCrisisLogs, label: 'Crisis logs', icon: AlertTriangle },
    { to: ROUTE_PATHS.adminResources, label: 'Resources', icon: Package },
]

const AdminSidebar = () => {
    const navigate = useNavigate()

    return (
        <aside className="w-64 border-r border-serene-primary/15 bg-white/70 p-4 backdrop-blur">
            <div className="mb-6 flex items-center gap-2 px-2">
                <Activity className="h-5 w-5 text-serene-primary" />
                <h2 className="font-display text-xl text-serene-ink">Admin</h2>
            </div>
            <nav className="space-y-1">
                {links.map((item) => {
                    const Icon = item.icon
                    return (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) =>
                                `flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
                                    isActive
                                        ? 'bg-serene-primary text-serene-on-primary'
                                        : 'text-serene-ink hover:bg-serene-primary/10'
                                }`
                            }
                        >
                            <Icon className="h-4 w-4" />
                            {item.label}
                        </NavLink>
                    )
                })}
            </nav>
            <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.adminLogin)}
                className="mt-8 inline-flex items-center gap-2 rounded-xl border border-serene-primary/20 px-3 py-2 text-sm text-serene-ink hover:bg-serene-primary/10"
            >
                <LogOut className="h-4 w-4" />
                Đổi tài khoản
            </button>
        </aside>
    )
}

export default AdminSidebar
