import { useEffect, useState } from 'react'
import { getPartners } from '../api'
import { LoadingSpinner, ErrorAlert, EmptyState, Badge } from '../components/ui'
import { MapPin, Phone, Mail, Wifi, WifiOff } from 'lucide-react'

const PARTNER_TYPE_COLORS = {
  SCA: 'purple',
  PSB: 'blue',
  RRB: 'green',
  'NBFC-MFI': 'yellow',
}

export default function Partners() {
  const [partners, setPartners] = useState([])
  const [activeOnly, setActiveOnly] = useState(false)
  const [isLoading, setIsLoading]  = useState(true)
  const [error, setError]      = useState(null)

  const load = (active) => {
    setIsLoading(true)
    getPartners(active)
      .then(setPartners)
      .catch(e => setError(e?.message || 'Error fetching data'))
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load(activeOnly) }, [activeOnly])

  if (error) return <ErrorAlert message={error} />

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Channel Partners</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">SCA, PSB, RRB and NBFC-MFI lending branches</p>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={e => setActiveOnly(e.target.checked)}
            className="rounded"
          />
          Show active only
        </label>
      </div>

      {isLoading ? <div>Loading data...</div> : (!partners || partners.length === 0) ? (
        <div>No records found</div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Location</th>
                <th>NPA %</th>
                <th>Status</th>
                <th>Contact</th>
              </tr>
            </thead>
            <tbody>
              {partners?.map(p => (
                <tr key={p.id}>
                  <td className="font-semibold text-slate-800 dark:text-slate-200 max-w-xs">{p.name}</td>
                  <td>
                    <Badge variant={PARTNER_TYPE_COLORS[p.partner_type] ?? 'gray'}>
                      {p.partner_type}
                    </Badge>
                  </td>
                  <td>
                    <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400 text-xs">
                      <MapPin size={12} />
                      {p.lat?.toFixed(3) ?? 'N/A'}, {p.lng?.toFixed(3) ?? 'N/A'}
                    </span>
                  </td>
                  <td>
                    <span className={`font-semibold ${
                      p.npa_percentage > 12
                        ? 'text-red-600 dark:text-red-400'
                        : p.npa_percentage > 6
                          ? 'text-yellow-600 dark:text-yellow-400'
                          : 'text-green-600 dark:text-green-400'
                    }`}>
                      {p.npa_percentage?.toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    {p.is_active
                      ? <span className="flex items-center gap-1 text-green-700 dark:text-green-400 text-xs font-medium"><Wifi size={12} /> Active</span>
                      : <span className="flex items-center gap-1 text-red-600 dark:text-red-400 text-xs font-medium"><WifiOff size={12} /> Inactive</span>
                    }
                  </td>
                  <td className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
                    <div className="flex items-center gap-1"><Phone size={11} /> {p.contact_phone}</div>
                    <div className="flex items-center gap-1"><Mail size={11} /> {p.contact_email}</div>
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
