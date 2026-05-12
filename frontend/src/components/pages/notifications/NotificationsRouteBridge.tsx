import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ROUTE_PATHS } from '../../../routes/paths'
import { OPEN_NOTIFICATION_MODAL_EVENT } from './events'

export default function NotificationsRouteBridge() {
    const navigate = useNavigate()

    useEffect(() => {
        window.dispatchEvent(new Event(OPEN_NOTIFICATION_MODAL_EVENT))
        navigate(ROUTE_PATHS.home, { replace: true })
    }, [navigate])

    return null
}
