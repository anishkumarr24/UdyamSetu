import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Sidebar from './components/Sidebar'
import Dashboard    from './pages/Dashboard'
import Schemes      from './pages/Schemes'
import Partners     from './pages/Partners'
import Users        from './pages/Users'
import Applications from './pages/Applications'
import Apply        from './pages/Apply'
import Admin        from './pages/Admin'
import './index.css'

function ProtectedAdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user || user.role !== 'bank_admin') {
    return <Navigate to="/" replace />
  }
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="flex min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 transition-colors">
        <Sidebar />

        {/* Main content area – offset by sidebar width */}
        <main className="flex-1 ml-60 p-8 max-w-[1400px] min-h-screen bg-slate-50 dark:bg-slate-900">
          <Routes>
            <Route path="/"             element={<Dashboard />}    />
            <Route path="/schemes"      element={<Schemes />}      />
            <Route path="/partners"     element={<Partners />}     />
            <Route path="/users"        element={<Users />}        />
            <Route path="/applications" element={<Applications />} />
            <Route path="/apply"        element={<Apply />}        />
            <Route path="/admin/bank"   element={<ProtectedAdminRoute><Admin /></ProtectedAdminRoute>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
    </AuthProvider>
  )
}
