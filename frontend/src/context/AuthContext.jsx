import { createContext, useContext, useState, useEffect } from 'react'
import { getMe, loginUser, registerUser } from '../api'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const checkAuth = async () => {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        const userData = await getMe()
        setUser(userData)
      } catch (err) {
        localStorage.removeItem('token')
        setUser(null)
      }
    } else {
      setUser(null)
    }
    setLoading(false)
  }

  useEffect(() => {
    checkAuth()
  }, [])

  const login = async (email, password) => {
    const data = await loginUser({ email, password })
    localStorage.setItem('token', data.access_token)
    await checkAuth()
  }

  const register = async (userData) => {
    const data = await registerUser(userData)
    localStorage.setItem('token', data.access_token)
    await checkAuth()
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  const isAdmin = user?.role === 'bank_admin'
  const isCitizen = user?.role === 'citizen'
  const isAuthenticated = Boolean(user)

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth, isAdmin, isCitizen, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
