import { useEffect, useState } from 'react'
import { getApplications, updateApplicationStatus } from '../api'
import { LoadingSpinner, ErrorAlert, EmptyState, Badge } from '../components/ui'

const STATUS_OPTIONS = ['Pending', 'Under_Review', 'Approved', 'Disbursed']

const STATUS_COLORS = {
  Pending:      'yellow',
  Under_Review: 'blue',
  Approved:     'green',
  Disbursed:    'purple',
}

function fmt(n) {
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n?.toLocaleString('en-IN')}`
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function Applications() {
  const [apps, setApps]       = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [filter, setFilter]   = useState('')
  const [updating, setUpdating] = useState(null)

  const load = () => {
    setIsLoading(true)
    getApplications(filter ? { status: filter } : {})
      .then(setApps)
      .catch(e => setError(e?.message || 'Error fetching data'))
      .finally(() => setIsLoading(false))
  }

  useEffect(load, [filter])

  const handleStatusChange = async (id, status) => {
    setUpdating(id)
    try {
      const updated = await updateApplicationStatus(id, status)
      setApps(prev => prev?.map(a => a.id === id ? updated : a))
    } catch (e) {
      alert('Failed to update status: ' + e.message)
    } finally {
      setUpdating(null)
    }
  }

  if (error) return <ErrorAlert message={error} />

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Loan Applications</h1>
          <p className="text-sm text-slate-500 mt-1">Track and manage all submitted applications</p>
        </div>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="px-4 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
      </div>

      {isLoading ? <div>Loading data...</div> : (!apps || apps.length === 0) ? (
        <div>No records found</div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Amount</th>
                <th>Tenure</th>
                <th>Moratorium</th>
                <th>Status</th>
                <th>Created</th>
                <th>Update Status</th>
              </tr>
            </thead>
            <tbody>
              {apps?.map(a => (
                <tr key={a.id}>
                  <td className="font-mono text-xs text-slate-400">{a.id.slice(0, 8)}…</td>
                  <td className="font-semibold">{fmt(a.amount)}</td>
                  <td className="text-slate-600">{a.tenure_months} mo</td>
                  <td className="text-slate-600">{a.moratorium_months} mo</td>
                  <td><Badge variant={STATUS_COLORS[a.status]}>{a.status.replace('_', ' ')}</Badge></td>
                  <td className="text-slate-500 text-xs">{fmtDate(a.created_at)}</td>
                  <td>
                    <select
                      value={a.status}
                      disabled={updating === a.id}
                      onChange={e => handleStatusChange(a.id, e.target.value)}
                      className="text-xs px-2 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-300 disabled:opacity-50"
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s} value={s}>{s.replace('_', ' ')}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
