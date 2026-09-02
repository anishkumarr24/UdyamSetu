import { useEffect, useState } from 'react'
import { getSchemes } from '../api'
import { LoadingSpinner, ErrorAlert, EmptyState, Badge } from '../components/ui'

function fmt(n) {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n?.toLocaleString('en-IN')}`
}

export default function Schemes() {
  const [schemes, setSchemes] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    getSchemes()
      .then(setSchemes)
      .catch(e => setError(e?.message || 'Error fetching data'))
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) return <div>Loading data...</div>
  if (error)   return <ErrorAlert message={error} />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Loan Schemes</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">NSFDC financial assistance programmes</p>
      </div>

      {(!schemes || schemes.length === 0) ? (
        <div>No records found</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {schemes?.map(s => (
            <div key={s.id} className="card flex flex-col gap-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-bold text-slate-800 dark:text-slate-100 leading-snug">{s.name}</h2>
                <Badge variant="blue">{s.required_category}</Badge>
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">{s.description}</p>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2">
                  <p className="text-slate-500 dark:text-slate-400 mb-0.5">Max Loan</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{fmt(s.max_amount)}</p>
                </div>
                <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2">
                  <p className="text-slate-500 dark:text-slate-400 mb-0.5">Max Income</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{fmt(s.max_income)}</p>
                </div>
                <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2">
                  <p className="text-slate-500 dark:text-slate-400 mb-0.5">Interest Rate</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{s.base_interest_rate}% p.a.</p>
                </div>
                <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2">
                  <p className="text-slate-500 dark:text-slate-400 mb-0.5">Moratorium</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">
                    {s.min_moratorium_months === s.max_moratorium_months
                      ? `${s.min_moratorium_months} mo`
                      : `${s.min_moratorium_months}–${s.max_moratorium_months} mo`}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
