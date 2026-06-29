import type { ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import { AuthProvider, useAuth } from './auth'

import Login from './pages/Login'
import Register from './pages/Register'
import RequestsList from './pages/RequestsList'
import CreateRequest from './pages/CreateRequest'

function AuthGuard({ children }: { children: ReactNode }) {
    const { isAuthenticated } = useAuth()
    return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function GuestGuard({ children }: { children: ReactNode }) {
    const { isAuthenticated } = useAuth()
    return isAuthenticated ? <Navigate to="/requests" replace /> : <>{children}</>
}

export default function App() {
    return (
        <AuthProvider>
        <BrowserRouter>
            <Routes>
            <Route path="/login" element={<GuestGuard><Login /></GuestGuard>} />
            <Route path="/register" element={<GuestGuard><Register /></GuestGuard>} />
            <Route path="/requests" element={<AuthGuard><RequestsList /></AuthGuard>} />
            <Route path="/requests/new" element={<AuthGuard><CreateRequest /></AuthGuard>} />
            <Route path="*" element={<Navigate to="/requests" replace />} />
            </Routes>
        </BrowserRouter>
        </AuthProvider>
    )
}
