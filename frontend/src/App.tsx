import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import Login from './components/auth/Login'
import Register from './components/auth/Register'
import Home from './components/pages/Home'
import Landing from './components/pages/Landing'
import Main from './components/layout/Main'
import Chat from './components/chat/Chat'
import Reflect from './components/pages/Reflect'
import Resources from './components/pages/Resources'
import Connect from './components/pages/Connect'
import ScrollToHash from './utils/ScrollToHash'




export default function App() {
  return (
    <BrowserRouter>
      <ScrollToHash />
      <Routes>
        <Route path="/" element={<Navigate to="/landing" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/landing" element={<Landing />} />

        <Route path="/serene" element={<Main />}>
          <Route index element={<Home />} />
          <Route path='chat' element={<Chat />} />
          <Route path='reflect' element={<Reflect />} />
          <Route path='resources' element={<Resources />} />
          <Route path='connect' element={<Connect />} />
        </Route>

        <Route path="*" element={<Navigate to="/landing" replace />} />

      </Routes>
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