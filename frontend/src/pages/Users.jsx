import { useEffect, useState } from 'react'
import { getUsers } from '../api'
import { LoadingSpinner, ErrorAlert, EmptyState, Badge } from '../components/ui'
import { CheckCircle2, XCircle } from 'lucide-react'

const CATEGORY_COLORS = {
  SC: 'blue', ST: 'purple', OBC: 'yellow', General: 'gray',
}

function BoolIcon({ val }) {
  return val
    ? <CheckCircle2 size={14} className="text-green-500" />
    : <XCircle size={14} className="text-slate-300" />
}

function fmt(n) {
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(1)} L`
  return `₹${n?.toLocaleString('en-IN')}`
}

export default function Users() {
  const [users, setUsers]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    getUsers()
      .then(setUsers)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = users.filter(u =>
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.category.toLowerCase().includes(search.toLowerCase()) ||
    u.project_domain.toLowerCase().includes(search.toLowerCase())
  )

  if (error) return <ErrorAlert message={error} />

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Beneficiaries</h1>
          <p className="text-sm text-slate-500 mt-1">Registered loan applicants</p>
        </div>
        <input
          type="search"
          placeholder="Search by name, category…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="px-4 py-2 text-sm rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300 w-64"
        />
      </div>

      {loading ? <LoadingSpinner /> : filtered.length === 0 ? (
        <EmptyState title="No beneficiaries found" description="Create users via the API or adjust your search." />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Age / Gender</th>
                <th>Category</th>
                <th>Annual Income</th>
                <th>Domain</th>
                <th>Requested</th>
                <th>Score</th>
                <th title="Udyam / Caste / Income">Docs</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(u => (
                <tr key={u.id}>
                  <td className="font-medium text-slate-800">{u.name}</td>
                  <td className="text-slate-500">{u.age} · {u.gender}</td>
                  <td><Badge variant={CATEGORY_COLORS[u.category] ?? 'gray'}>{u.category}</Badge></td>
                  <td>{fmt(u.annual_income)}</td>
                  <td className="text-slate-600 max-w-[140px] truncate">{u.project_domain}</td>
                  <td className="font-medium">{fmt(u.requested_amount)}</td>
                  <td>
                    <span className={`font-semibold text-sm ${
                      u.readiness_score >= 70 ? 'text-green-600' :
                      u.readiness_score >= 40 ? 'text-yellow-600' : 'text-red-500'
                    }`}>
                      {u.readiness_score.toFixed(0)}
                    </span>
                  </td>
                  <td>
                    <div className="flex items-center gap-1.5">
                      <span title="Udyam"><BoolIcon val={u.has_udyam} /></span>
                      <span title="Caste Cert"><BoolIcon val={u.has_caste_cert} /></span>
                      <span title="Income Cert"><BoolIcon val={u.has_income_cert} /></span>
                    </div>
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
