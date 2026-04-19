import { BrowserRouter } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import ScrollToHash from './utils/ScrollToHash'
import AppRoutes from './routes/AppRoutes'




export default function App() {
  return (
    <BrowserRouter>
      <ScrollToHash />
      <AppRoutes />
      <ToastContainer
        position="top-right"
        autoClose={2400}
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