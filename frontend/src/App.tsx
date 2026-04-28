import { BrowserRouter } from 'react-router-dom'
import ScrollToHash from './utils/ScrollToHash'
import AppRoutes from './routes/AppRoutes'
import { ToastContainer } from 'react-toastify'




export default function App() {
  return (
    <BrowserRouter>
      <ScrollToHash />
      <AppRoutes />
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
  )
}