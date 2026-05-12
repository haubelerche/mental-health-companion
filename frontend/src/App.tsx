import { BrowserRouter } from 'react-router-dom'
import ScrollToHash from './utils/ScrollToHash'
import AppRoutes from './routes/AppRoutes'
import { ToastContainer } from 'react-toastify'
import { ThemeProvider } from './contexts/ThemeContext'
import { NotificationProvider } from './contexts/NotificationContext'
import NotificationContainer from './components/pages/notifications/NotificationToast'
import NotificationSetup from './components/pages/notifications/NotificationSetup'
import RealtimeNotificationAssistantBridge from './components/assistants/RealtimeNotificationAssistantBridge'


export default function App() {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <BrowserRouter>
          <NotificationSetup />
          <ScrollToHash />
          <AppRoutes />
          <RealtimeNotificationAssistantBridge />
          <NotificationContainer />
          <ToastContainer
            position="top-right"
            autoClose={2000}
            hideProgressBar={false}
            newestOnTop
            closeOnClick
            pauseOnFocusLoss
            pauseOnHover
            draggable
            theme="light"
          />
        </BrowserRouter>
      </NotificationProvider>
    </ThemeProvider>
  )
}
