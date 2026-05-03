import { BrowserRouter } from 'react-router-dom'
import ScrollToHash from './utils/ScrollToHash'
import AppRoutes from './routes/AppRoutes'




export default function App() {
  return (
    <BrowserRouter>
      <ScrollToHash />
      <AppRoutes />
    </BrowserRouter>
  )
}