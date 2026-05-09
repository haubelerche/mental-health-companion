import { Activity, AlertTriangle, BarChart3, Bell, LayoutDashboard, LogOut, Mail, Package, Shield, Users } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { ROUTE_PATHS } from '../../../routes/paths'
import { adminAuthService } from '../../../services/adminAuthService'

const links = [
    { to: ROUTE_PATHS.adminDashboard, label: 'Tổng quan', icon: LayoutDashboard },
    { to: ROUTE_PATHS.adminAnalytics, label: 'Phân tích', icon: BarChart3 },
    { to: ROUTE_PATHS.adminUsers, label: 'Người dùng', icon: Users },
    { to: ROUTE_PATHS.adminNotifications, label: 'Thông báo', icon: Bell },
    { to: ROUTE_PATHS.adminLetters, label: 'Kiểm duyệt thư', icon: Mail },
    { to: ROUTE_PATHS.adminAuditLogs, label: 'Nhật ký Admin', icon: Shield },
    { to: ROUTE_PATHS.adminCrisisLogs, label: 'Nhật ký khẩn', icon: AlertTriangle },
    { to: ROUTE_PATHS.adminResources, label: 'Tài nguyên', icon: Package },
]

const AdminSidebar = () => {
    const navigate = useNavigate()

    return (
        <aside className="admin-sidebar">
            {/* Brand */}
            <div className="admin-sidebar-brand">
                <div className="admin-sidebar-brand-icon">
                    <Activity size={20} />
                </div>
                <div>
                    <h2 className="admin-sidebar-brand-title">Serene</h2>
                    <p className="admin-sidebar-brand-sub">Bảng điều khiển</p>
                </div>
            </div>

            {/* Nav */}
            <nav className="admin-sidebar-nav">
                <p className="admin-sidebar-section-label">MENU CHÍNH</p>
                {links.map((item) => {
                    const Icon = item.icon
                    return (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) =>
                                `admin-sidebar-link ${isActive ? 'active' : ''}`
                            }
                        >
                            <Icon size={18} />
                            <span>{item.label}</span>
                        </NavLink>
                    )
                })}
            </nav>

            {/* Footer */}
            <div className="admin-sidebar-footer">
                <button
                    type="button"
                    onClick={async () => {
                        await adminAuthService.logout().catch(() => {})
                        navigate(ROUTE_PATHS.adminLogin)
                    }}
                    className="admin-sidebar-logout"
                >
                    <LogOut size={16} />
                    Đổi tài khoản
                </button>
            </div>
        </aside>
    )
}

export default AdminSidebar
