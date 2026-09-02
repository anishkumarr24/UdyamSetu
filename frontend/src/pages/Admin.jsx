/**
 * Admin.jsx – Bank Officer Admin Portal
 */

import { useState, useEffect } from 'react'
import { adminGetApplications, adminSimulateNpa, getPartners } from '../api'
import { useLanguage } from '../context/LanguageContext'
import {
  Loader2, AlertTriangle, CheckCircle2, ShieldAlert,
  Activity, Users, FileCheck, TrendingDown, ChevronDown,
} from 'lucide-react'

function fmt(n) {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${Number(n).toLocaleString('en-IN')}`
}

const SCORE_COLOR = (s) => {
  if (s >= 80) return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
  if (s >= 50) return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20'
  return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20'
}

function NpaSliderRow({ partner, onNpaChange }) {
  const { t } = useLanguage()
  const [npa,      setNpa]      = useState(partner.npa_percentage)
  const [loading,  setLoading]  = useState(false)
  const [result,   setResult]   = useState(null)
  const [debTimer, setDebTimer] = useState(null)

  const handleSlide = (val) => {
    setNpa(val)
    if (debTimer) clearTimeout(debTimer)
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await adminSimulateNpa({ partner_id: partner.id, npa_percentage: val })
        setResult(res)
        onNpaChange?.(partner.id, val, res.is_active)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }, 400)
    setDebTimer(timer)
  }

  const breached = npa > 8
  const pct = ((npa - 1) / (15 - 1)) * 100

  return (
    <div className={`rounded-2xl border-2 p-4 transition-all duration-300 ${
      breached ? 'border-red-300 dark:border-red-900/50 bg-red-50 dark:bg-red-900/10' : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800'
    }`}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-800 dark:text-slate-100 leading-tight truncate">{partner.name}</p>
          <span className="badge badge-blue text-[10px] mt-0.5">{partner.partner_type}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {loading && <Loader2 size={14} className="animate-spin text-slate-400" />}
          {!loading && result && (
            result.is_active
              ? <CheckCircle2 size={16} className="text-green-500" />
              : <ShieldAlert size={16} className="text-red-500" />
          )}
          <span className={`text-lg font-extrabold ${breached ? 'text-red-600 dark:text-red-400' : 'text-slate-800 dark:text-slate-200'}`}>
            {npa.toFixed(1)}%
          </span>
        </div>
      </div>

      <div className="space-y-1">
        <input
          type="range" min={1} max={15} step={0.5} value={npa}
          onChange={e => handleSlide(Number(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer slider-thumb"
          style={{
            background: breached
              ? `linear-gradient(to right, #dc2626 ${pct}%, #fecaca40 ${pct}%)`
              : `linear-gradient(to right, #3b82f6 ${pct}%, #64748b40 ${pct}%)`
          }}
        />
        <div className="flex justify-between text-[10px] text-slate-500 dark:text-slate-500">
          <span>1% ({t('healthyLabel')})</span>
          <span className="text-amber-500 dark:text-amber-400 font-semibold">8% {t('thresholdLabel')}</span>
          <span className="text-red-400">15% ({t('criticalLabel')})</span>
        </div>
      </div>

      {breached && (
        <div className="mt-3 flex items-start gap-2 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-900/50 rounded-xl px-3 py-2.5">
          <AlertTriangle size={15} className="text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-bold text-red-800 dark:text-red-300">{t('npaExceededTitle')}</p>
            <p className="text-[11px] text-red-600 dark:text-red-400/80 leading-snug mt-0.5">
              {t('npaExceededDesc1')} <span className="font-bold">{t('npaExceededDescBold')}</span> {t('npaExceededDesc2')}
            </p>
          </div>
        </div>
      )}
      {!breached && result && (
        <p className="mt-2 text-[11px] text-green-600 dark:text-green-400 font-medium">
          {t('branchActive')}
        </p>
      )}
    </div>
  )
}

function ApplicationsTable() {
  const { t } = useLanguage()
  const [apps,    setApps]    = useState([])
  const [loading, setLoading] = useState(true)
  const [statusMap, setStatusMap] = useState({})

  useEffect(() => {
    adminGetApplications()
      .then(data => {
        setApps(data)
        const init = {}
        data.forEach(a => { init[a.id] = a.status })
        setStatusMap(init)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleStatusChange = (id, val) => {
    setStatusMap(m => ({ ...m, [id]: val }))
  }

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 size={28} className="animate-spin text-blue-400" />
    </div>
  )

  const sanctioned   = Object.values(statusMap).filter(s => s === 'Sanctioned').length
  const underReview  = Object.values(statusMap).filter(s => s === 'Under Review').length
  const totalAmount  = apps.reduce((sum, a) => sum + a.requested_amount, 0)
  
  const STATUS_OPTIONS = [
    { val: 'Pending', label: t('statusPending') },
    { val: 'Under Review', label: t('statusUnderReview') },
    { val: 'Sanctioned', label: t('statusSanctioned') }
  ]

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: t('totalApps'),       value: apps.length,    icon: Users,       color: 'blue'   },
          { label: t('sanctionedApps'),  value: sanctioned,     icon: FileCheck,   color: 'green'  },
          { label: t('underReviewApps'), value: underReview,    icon: Activity,    color: 'purple' },
          { label: t('totalRequested'),  value: fmt(totalAmount),icon: TrendingDown,color: 'amber'  },
        ].map(({ label, value, icon: Icon, color }) => {
          const c = {
            blue:   'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400',
            green:  'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400',
            purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400',
            amber:  'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400',
          }[color]
          return (
            <div key={label} className={`${c} rounded-2xl px-4 py-3 flex items-center gap-3`}>
              <Icon size={16} className="opacity-70 shrink-0" />
              <div>
                <p className="text-[10px] font-semibold opacity-70 uppercase tracking-wide">{label}</p>
                <p className="text-lg font-extrabold leading-tight">{value}</p>
              </div>
            </div>
          )
        })}
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              {[t('appId'), t('applicantName'), t('domainCol'), t('amountCol'), t('schemeCol'), t('scoreCol'), t('submittedCol'), t('statusCol')].map(h => (
                <th key={h} className="px-4 py-3 text-left text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {apps.map(app => {
              const st = statusMap[app.id] ?? app.status
              return (
                <tr key={app.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">{app.id}</td>
                  <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">{app.applicant_name}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 whitespace-nowrap">{app.domain}</td>
                  <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">{fmt(app.requested_amount)}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300 whitespace-nowrap text-xs">{app.matched_scheme}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-lg text-xs font-bold ${SCORE_COLOR(app.readiness_score)}`}>
                      {app.readiness_score}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">{app.submitted_on}</td>
                  <td className="px-4 py-3">
                    <div className="relative">
                      <select
                        value={st}
                        onChange={e => handleStatusChange(app.id, e.target.value)}
                        className={`appearance-none pr-7 pl-2 py-1.5 text-xs font-semibold rounded-lg border cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-300 dark:bg-slate-900 dark:text-slate-100 ${
                          st === 'Sanctioned'   ? 'border-green-300  dark:border-green-700  bg-green-50  dark:bg-green-900/20  text-green-700  dark:text-green-300'
                          : st === 'Under Review' ? 'border-blue-300   dark:border-blue-700   bg-blue-50   dark:bg-blue-900/20   text-blue-700   dark:text-blue-300'
                                                  : 'border-yellow-300 dark:border-yellow-700 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300'
                        }`}
                      >
                        {STATUS_OPTIONS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
                      </select>
                      <ChevronDown size={11} className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 opacity-50" />
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function NpaControlPanel() {
  const { t } = useLanguage()
  const [partners, setPartners] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [npaState, setNpaState] = useState({})

  useEffect(() => {
    getPartners()
      .then(data => {
        setPartners(data)
        const init = {}
        data.forEach(p => { init[p.id] = { npa: p.npa_percentage, is_active: p.is_active } })
        setNpaState(init)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleNpaChange = (id, npa, is_active) => {
    setNpaState(s => ({ ...s, [id]: { npa, is_active } }))
  }

  const bypassed = Object.values(npaState).filter(s => !s.is_active).length

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <Activity size={17} className="text-purple-600 dark:text-purple-400" />
            {t('npaPanelTitle')}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {t('npaPanelDesc')}
          </p>
        </div>
        {bypassed > 0 && (
          <div className="flex items-center gap-1.5 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-900/50 text-red-700 dark:text-red-400 rounded-xl px-3 py-1.5 text-xs font-bold shrink-0">
            <ShieldAlert size={13} />
            {bypassed} {bypassed > 1 ? t('branchesBypassed') : t('branchBypassed')}
          </div>
        )}
      </div>

      {loading
        ? <div className="flex justify-center py-10"><Loader2 size={24} className="animate-spin text-blue-400" /></div>
        : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {partners.map(p => (
              <NpaSliderRow
                key={p.id}
                partner={{ ...p, npa_percentage: npaState[p.id]?.npa ?? p.npa_percentage }}
                onNpaChange={handleNpaChange}
              />
            ))}
          </div>
        )
      }
    </div>
  )
}

export default function Admin() {
  const { t } = useLanguage()
  return (
    <div className="space-y-10 max-w-7xl mx-auto">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-purple-700 flex items-center justify-center shrink-0">
          <ShieldAlert size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('adminHeader')}</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
            {t('adminDesc')}
          </p>
        </div>
      </div>

      <section className="card">
        <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-6 flex items-center gap-2 pb-4 border-b border-slate-100 dark:border-slate-800">
          <Users size={17} className="text-blue-600 dark:text-blue-500" />
          {t('submittedApps')}
        </h2>
        <ApplicationsTable />
      </section>

      <section className="card">
        <NpaControlPanel />
      </section>
    </div>
  )
}
