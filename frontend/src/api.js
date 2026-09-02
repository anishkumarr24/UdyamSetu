import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Engine API (algorithmic endpoints – mounted at /api, not /api/v1)
const engineApi = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
})

// Interceptors to inject JWT from localStorage
const authInterceptor = (config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}
api.interceptors.request.use(authInterceptor)
engineApi.interceptors.request.use(authInterceptor)

// Handle 401 Unauthorized globally
const unauthorizedInterceptor = (error) => {
  if (error.response && error.response.status === 401) {
    localStorage.removeItem('token')
    // Optionally force a reload or redirect here if needed
  }
  return Promise.reject(error)
}
api.interceptors.response.use((res) => res, unauthorizedInterceptor)
engineApi.interceptors.response.use((res) => res, unauthorizedInterceptor)

// ── Auth ──────────────────────────────────────────────────────────────────
export const registerUser = (data) => api.post('/auth/register', data).then(r => r.data)
export const loginUser = (data) => {
  const formData = new URLSearchParams()
  formData.append('username', data.email)
  formData.append('password', data.password)
  return api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  }).then(r => r.data)
}
export const getMe = () => api.get('/auth/me').then(r => r.data)


export const fetchDigiLockerUrl = () => api.get('/digilocker/auth-url').then(r => r.data)
export const verifyDigilocker = (docType) => api.post('/digilocker/verify-fetch', {
  document_type: docType,
  access_token: 'dummy_token' // Simulated token for demo purposes
}).then(r => r.data)

// ── Engine ────────────────────────────────────────────────────────────────
export const matchScheme = (data) => engineApi.post('/match-scheme', data).then(r => r.data)
export const calculateEmi = (data) => engineApi.post('/calculate-emi', data).then(r => r.data)
export const findPartners = (data) => engineApi.post('/find-partners', data).then(r => r.data)
export const adminGetApplications = () => engineApi.get('/admin/applications').then(r => r.data)
export const adminSimulateNpa = (data) => engineApi.post('/admin/simulate-npa', data).then(r => r.data)

// ── Users ─────────────────────────────────────────────────────────────────
export const getUsers = () => api.get('/users/').then(r => r.data)
export const getUser = (id) => api.get(`/users/${id}`).then(r => r.data)
export const createUser = (data) => api.post('/users/', data).then(r => r.data)
export const updateUser = (id, data) => api.put(`/users/${id}`, data).then(r => r.data)
export const deleteUser = (id) => api.delete(`/users/${id}`)

// ── Schemes ───────────────────────────────────────────────────────────────
export const getSchemes = () => api.get('/schemes/').then(r => r.data)
export const getScheme = (id) => api.get(`/schemes/${id}`).then(r => r.data)
export const createScheme = (data) => api.post('/schemes/', data).then(r => r.data)
export const updateScheme = (id, data) => api.put(`/schemes/${id}`, data).then(r => r.data)
export const deleteScheme = (id) => api.delete(`/schemes/${id}`)

// ── Channel Partners ──────────────────────────────────────────────────────
export const getPartners = (activeOnly = false) =>
  api.get('/partners/', { params: { active_only: activeOnly } }).then(r => r.data)
export const getPartner = (id) => api.get(`/partners/${id}`).then(r => r.data)
export const createPartner = (data) => api.post('/partners/', data).then(r => r.data)
export const updatePartner = (id, data) => api.put(`/partners/${id}`, data).then(r => r.data)
export const deletePartner = (id) => api.delete(`/partners/${id}`)

// ── Loan Applications ─────────────────────────────────────────────────────
export const getApplications = (params = {}) =>
  api.get('/applications/', { params }).then(r => r.data)
export const getApplication = (id) => api.get(`/applications/${id}`).then(r => r.data)
export const createApplication = (data) => api.post('/applications/', data).then(r => r.data)
export const updateApplicationStatus = (id, status) =>
  api.patch(`/applications/${id}/status`, null, { params: { status } }).then(r => r.data)
export const deleteApplication = (id) => api.delete(`/applications/${id}`)

export default api
