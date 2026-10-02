import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getApplications, updateApplicationStatus } from '../api'
import { useAuth } from '../context/AuthContext'
import { LoadingSpinner, ErrorAlert, EmptyState, Badge } from '../components/ui'
import { FileText, Wand2, Clock, CheckCircle2, AlertCircle } from 'lucide-react'

const STATUS_OPTIONS = ['Pending', 'Under_Review', 'Approved', 'Disbursed', 'Rejected']

const STATUS_COLORS = {
  Pending:      'yellow',
  Under_Review: 'blue',
  Approved:     'green',
  Disbursed:    'purple',
  Rejected:     'red',
}

function fmt(n) {
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n?.toLocaleString('en-IN')}`
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function Applications() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'bank_admin'
  const [apps, setApps]             = useState([])
  const [isLoading, setIsLoading]   = useState(true)
  const [error, setError]           = useState(null)
  const [filter, setFilter]         = useState('')
  const [updating, setUpdating]     = useState(null)

  const load = () => {
    setIsLoading(true)
    getApplications(filter ? { status: filter } : {})
      .then(setApps)
      .catch(e => setError(e?.response?.data?.detail || e?.message || 'Error fetching data'))
      .finally(() => setIsLoading(false))
  }

  useEffect(load, [filter])

  const handleStatusChange = async (id, status) => {
    setUpdating(id)
    try {
      const updated = await updateApplicationStatus(id, status)
      setApps(prev => prev?.map(a => a.id === id ? { ...a, status: updated.status } : a))
    } catch (e) {
      alert('Failed to update status: ' + (e?.response?.data?.detail || e?.message))
    } finally {
      setUpdating(null)
    }
  }

  if (error) return <ErrorAlert message={error} />

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
              isAdmin ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300' : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
            }`}>
              {isAdmin ? 'Bank Officer Review' : 'Citizen Portal'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
            {isAdmin ? 'Loan Applications Management' : 'My Loan Applications'}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {isAdmin 
              ? 'Review, verify documents, and disburse submitted loan applications across branches.'
              : 'Track the status and progress of your submitted NSFDC loan scheme applications.'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="px-4 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>

          {!isAdmin && (
            <Link
              to="/apply"
              className="btn-primary text-xs py-2 px-3 gap-1.5 shrink-0"
            >
              <Wand2 size={14} />
              New Application
            </Link>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="py-12 flex justify-center text-slate-400 text-sm">Loading applications…</div>
      ) : (!apps || apps.length === 0) ? (
        <div className="card p-12 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
            <FileText size={24} />
          </div>
          <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">
            {isAdmin ? 'No applications found' : 'You haven’t applied for any loan schemes yet'}
          </h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            {isAdmin
              ? 'There are currently no submitted applications matching the selected criteria.'
              : 'Use the 3-step AI loan readiness tool to find your best scheme match and submit your application.'}
          </p>
          {!isAdmin && (
            <Link to="/apply" className="btn-primary mx-auto py-2.5 px-5">
              <Wand2 size={16} />
              Apply for a Scheme
            </Link>
          )}
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>App ID</th>
                {isAdmin && <th>Applicant</th>}
                <th>Scheme</th>
                <th>Disbursing Branch</th>
                <th>Amount</th>
                <th>Tenure</th>
                <th>Moratorium</th>
                <th>Status</th>
                <th>Submitted</th>
                {isAdmin && <th>Action / Status</th>}
              </tr>
            </thead>
            <tbody>
              {apps.map(a => (
                <tr key={a.id}>
                  <td className="font-mono text-xs text-slate-400">{a.id.slice(0, 8)}…</td>
                  {isAdmin && (
                    <td className="font-medium text-slate-800 dark:text-slate-100">
                      {a.applicant_name || 'Beneficiary'}
                    </td>
                  )}
                  <td className="font-semibold text-slate-800 dark:text-slate-200">
                    {a.scheme_name || 'NSFDC Scheme'}
                  </td>
                  <td className="text-xs text-slate-600 dark:text-slate-400 max-w-[180px] truncate" title={a.partner_name}>
                    {a.partner_name || 'Channel Partner'}
                  </td>
                  <td className="font-semibold text-blue-700 dark:text-blue-400">{fmt(a.amount)}</td>
                  <td className="text-slate-600 dark:text-slate-400">{a.tenure_months} mo</td>
                  <td className="text-slate-600 dark:text-slate-400">{a.moratorium_months} mo</td>
                  <td>
                    <Badge variant={STATUS_COLORS[a.status] || 'yellow'}>
                      {a.status.replace('_', ' ')}
                    </Badge>
                  </td>
                  <td className="text-slate-500 text-xs">{fmtDate(a.created_at)}</td>
                  {isAdmin && (
                    <td>
                      <select
                        value={a.status}
                        disabled={updating === a.id}
                        onChange={e => handleStatusChange(a.id, e.target.value)}
                        className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-300 disabled:opacity-50"
                      >
                        {STATUS_OPTIONS.map(s => (
                          <option key={s} value={s}>{s.replace('_', ' ')}</option>
                        ))}
                      </select>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
