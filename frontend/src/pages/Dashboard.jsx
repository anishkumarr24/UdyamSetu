/**
 * CitizenDashboard.jsx – Post-match Citizen Dashboard
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { calculateEmi, findPartners } from '../api'
import {
  MapContainer, TileLayer, Marker, Popup, Polyline
} from 'react-leaflet'
import L from 'leaflet'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, Cell,
} from 'recharts'
import {
  Loader2, Download, CheckCircle2, Building2, MapPin,
  Wallet, TrendingUp, Clock, BadgePercent,
} from 'lucide-react'
import { jsPDF } from 'jspdf'
import { useLanguage } from '../context/LanguageContext'
import { useTheme } from '../context/ThemeContext'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const USER_LAT = 22.90
const USER_LNG = 88.38
const DEFAULT_RATE = 6.5

const makeIcon = (color) =>
  new L.DivIcon({
    className: '',
    html: `<div style="
      width:22px;height:22px;border-radius:50% 50% 50% 0;
      background:${color};border:2.5px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,.35);
      transform:rotate(-45deg);
    "></div>`,
    iconSize:   [22, 22],
    iconAnchor: [11, 22],
    popupAnchor:[0,  -24],
  })

const USER_ICON    = makeIcon('#1d4ed8')
const PARTNER_ICON = makeIcon('#16a34a')
const BYPASSED_ICON= makeIcon('#dc2626')

function fmt(n) {
  if (!n && n !== 0) return '—'
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${Number(n).toLocaleString('en-IN')}`
}

function EMITooltip({ active, payload, label }) {
  const { t } = useLanguage()
  if (!active || !payload?.length) return null
  const interest  = payload.find(p => p.dataKey === 'interest_paid')?.value  ?? 0
  const principal = payload.find(p => p.dataKey === 'principal_paid')?.value ?? 0
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2.5 shadow-lg text-xs space-y-1">
      <p className="font-bold text-slate-700 dark:text-slate-200">{t('month')} {label}</p>
      <p className="text-blue-600 dark:text-blue-400">{t('interestPaid')}: <span className="font-semibold">{fmt(interest)}</span></p>
      <p className="text-emerald-600 dark:text-emerald-400">{t('principalPaid')}: <span className="font-semibold">{fmt(principal)}</span></p>
      <p className="text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-1">{t('total')}: {fmt(interest + principal)}</p>
    </div>
  )
}

function MetricCard({ label, value, sub, icon: Icon, accent }) {
  const accents = {
    blue:   { bg: 'bg-blue-50 dark:bg-blue-900/20',   text: 'text-blue-700 dark:text-blue-400',   icon: 'text-blue-400'   },
    green:  { bg: 'bg-green-50 dark:bg-green-900/20',  text: 'text-green-700 dark:text-green-400',  icon: 'text-green-400'  },
    amber:  { bg: 'bg-amber-50 dark:bg-amber-900/20',  text: 'text-amber-700 dark:text-amber-400',  icon: 'text-amber-400'  },
    purple: { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-400', icon: 'text-purple-400' },
  }
  const c = accents[accent] ?? accents.blue
  return (
    <div className={`${c.bg} rounded-2xl px-4 py-4 flex items-start gap-3`}>
      <Icon size={18} className={`${c.icon} mt-0.5 shrink-0`} />
      <div>
        <p className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
        <p className={`text-xl font-extrabold ${c.text} leading-tight mt-0.5`}>{value}</p>
        {sub && <p className="text-[10px] text-slate-500 dark:text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function Slider({ label, min, max, step, value, onChange, format }) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-baseline">
        <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">{label}</label>
        <span className="text-sm font-bold text-blue-700 dark:text-blue-400">{format ? format(value) : value}</span>
      </div>
      <div className="relative">
        <input
          type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange(Number(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer slider-thumb"
          style={{
            background: `linear-gradient(to right, #3b82f6 ${pct}%, #64748b40 ${pct}%)`
          }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-slate-500 dark:text-slate-500">
        <span>{format ? format(min) : min}</span>
        <span>{format ? format(max) : max}</span>
      </div>
    </div>
  )
}

function MoratoriumVisualizer() {
  const { t } = useLanguage()
  const { theme } = useTheme()
  const [principal,   setPrincipal]   = useState(50000)
  const [tenure,      setTenure]      = useState(24)
  const [moratorium,  setMoratorium]  = useState(3)
  const [emiData,     setEmiData]     = useState(null)
  const [loading,     setLoading]     = useState(false)
  const debounceRef = useRef(null)

  const fetchEmi = useCallback(async (p, t, m) => {
    if (t <= m) return
    setLoading(true)
    try {
      const data = await calculateEmi({
        principal: p,
        annual_interest_rate: DEFAULT_RATE,
        tenure_months: t,
        moratorium_months: m,
      })
      setEmiData(data)
    } catch (e) {
      console.error('EMI fetch error', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      fetchEmi(principal, tenure, moratorium)
    }, 300)
    return () => clearTimeout(debounceRef.current)
  }, [principal, tenure, moratorium, fetchEmi])

  const chartData = emiData?.schedule
    ? emiData.schedule.filter((_, i) => tenure <= 24 || i % 2 === 0)
    : []

  const gridColor = theme === 'dark' ? '#334155' : '#e2e8f0'
  const textColor  = theme === 'dark' ? '#64748b' : '#64748b'

  return (
    <div className="card bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 dark:border-slate-700 space-y-6">
      <div>
        <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <TrendingUp size={17} className="text-blue-600 dark:text-blue-500" />
          {t('moratoriumVisTitle')}
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">NSFDC Micro Finance · {DEFAULT_RATE}% p.a.</p>
      </div>

      <div className="space-y-5">
        <Slider label={t('loanAmount')} min={10000} max={140000} step={5000} value={principal}
          onChange={setPrincipal} format={fmt} />
        <Slider label={t('tenureSlider')} min={12} max={60} step={1} value={tenure}
          onChange={v => { setTenure(v); if (moratorium >= v) setMoratorium(v - 1) }}
          format={v => `${v} ${t('month')}s`} />
        <Slider label={t('moratoriumPeriod')} min={0} max={Math.min(12, tenure - 1)} step={1}
          value={moratorium} onChange={setMoratorium} format={v => `${v} ${t('month')}s`} />
      </div>

      {emiData ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-2 gap-3">
            <MetricCard label={t('postMoratoriumEmi')} value={fmt(emiData.regular_emi)}
              icon={Wallet} accent="blue" sub={`${tenure - moratorium} ${t('month')}s`} />
            <MetricCard label={t('moratoriumPayment')} value={fmt(emiData.moratorium_monthly_payment)}
              icon={Clock} accent="amber" sub={`${moratorium} ${t('month')}s`} />
            <MetricCard label={t('totalInterest')} value={fmt(emiData.total_interest_paid)}
              icon={BadgePercent} accent="purple" />
            <MetricCard label={t('totalPayable')} value={fmt(emiData.total_amount_payable)}
              icon={TrendingUp} accent="green" />
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
              {t('monthRepaymentBreakdown')}
            </p>
            {loading
              ? <div className="h-52 flex items-center justify-center"><Loader2 size={24} className="animate-spin text-blue-400" /></div>
              : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} margin={{ top: 0, right: 4, left: -16, bottom: 0 }} barSize={tenure <= 24 ? 12 : 6}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 9, fill: textColor }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: textColor }} tickLine={false} axisLine={false}
                    tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                  <Tooltip content={<EMITooltip />} />
                  <Legend wrapperStyle={{ fontSize: '11px', color: textColor }}
                    formatter={v => v === 'interest_paid' ? t('interestPaid') : t('principalPaid')} />
                  <Bar dataKey="interest_paid"  stackId="emi" fill="#60a5fa" radius={[0,0,3,3]} />
                  <Bar dataKey="principal_paid" stackId="emi" fill="#1d4ed8" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      ) : (
        <div className="flex items-center justify-center h-40">
          <Loader2 size={28} className="animate-spin text-blue-300" />
        </div>
      )}
    </div>
  )
}

function GISMap({ selectedBank, setSelectedBank, onPartnersLoaded }) {
  const { t } = useLanguage()
  const { theme } = useTheme()
  const [partners,  setPartners]  = useState([])
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    findPartners({ user_lat: USER_LAT, user_lng: USER_LNG, radius_km: 100 })
      .then(data => {
        setPartners(data.partners)
        onPartnersLoaded?.(data.partners)
        if (data.partners.length) setSelectedBank(data.partners[0].id)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const sel = partners.find(p => p.id === selectedBank)



  return (
    <div className="card bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 dark:border-slate-700 space-y-5">
      <div>
        <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <MapPin size={17} className="text-green-600 dark:text-green-500" />
          {t('gisRouterTitle')}
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t('gisRouterDesc')}</p>
      </div>

      <div className="rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-600" style={{ height: 300 }}>
        {!loading && (
          <MapContainer
            center={[USER_LAT, USER_LNG]}
            zoom={10}
            style={{ width: '100%', height: '100%' }}
            scrollWheelZoom={false}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />

            <Marker position={[USER_LAT, USER_LNG]} icon={USER_ICON}>
              <Popup>
                <strong>Your Location</strong><br />
                Bandel, West Bengal
              </Popup>
            </Marker>

            {partners.map(p => (
              <Marker key={p.id} position={[p.lat, p.lng]} icon={PARTNER_ICON}>
                <Popup>
                  <strong>{p.name}</strong><br />
                  {p.partner_type} · NPA {p.npa_percentage}%<br />
                  {p.distance_km} km away
                </Popup>
              </Marker>
            ))}

            {sel && (
              <Polyline
                positions={[[USER_LAT, USER_LNG], [sel.lat, sel.lng]]}
                color={theme === 'dark' ? '#60a5fa' : '#1d4ed8'} weight={2.5} dashArray="6 4"
              />
            )}
          </MapContainer>
        )}
        {loading && (
          <div className="h-full flex items-center justify-center bg-slate-50 dark:bg-slate-800">
            <Loader2 size={28} className="animate-spin text-blue-400" />
          </div>
        )}
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {partners.length === 0 && !loading && (
          <p className="text-sm text-slate-500 dark:text-slate-400">{t('noHealthyBanks')}</p>
        )}
        {partners.map((p, i) => (
          <label key={p.id} className={`flex items-start gap-3 rounded-xl px-3 py-3 cursor-pointer border transition-all ${
            selectedBank === p.id
              ? 'border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20'
              : 'border-slate-100 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}>
            <input
              type="radio" name="bank" value={p.id}
              checked={selectedBank === p.id}
              onChange={() => setSelectedBank(p.id)}
              className="mt-0.5 accent-blue-700"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 leading-snug truncate">{p.name}</p>
                <span className="badge badge-green shrink-0 text-[10px]">{p.distance_km} km</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="badge badge-blue text-[10px]">{p.partner_type}</span>
                <span className="text-[10px] text-slate-500">NPA {p.npa_percentage}%</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">{p.contact_phone} · {p.contact_email}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}

async function downloadDossier({ principal, tenure, moratorium, emiData, selectedBankName }) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const W = 210, PL = 18, PT = 22
  let y = PT

  doc.setFillColor(29, 78, 216)
  doc.rect(0, 0, W, 16, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.text('UdyamSetu – Bank-Ready Loan Dossier', PL, 10.5)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(7)
  doc.text(`Generated: ${new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}`, W - PL, 10.5, { align: 'right' })

  y = 26

  const section = (title) => {
    doc.setFillColor(241, 245, 249)
    doc.rect(PL - 2, y - 4, W - 2 * PL + 4, 8, 'F')
    doc.setTextColor(30, 41, 59)
    doc.setFontSize(9)
    doc.setFont('helvetica', 'bold')
    doc.text(title, PL, y)
    y += 8
  }
  const row = (label, value, bold = false) => {
    doc.setFontSize(9)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(100, 116, 139)
    doc.text(label, PL, y)
    doc.setTextColor(15, 23, 42)
    doc.setFont('helvetica', bold ? 'bold' : 'normal')
    doc.text(String(value), PL + 58, y)
    y += 6
  }

  section('Beneficiary Profile')
  row('Applicant Name', 'Rajesh Kumar', true)
  row('Category', 'SC (Scheduled Caste)')
  row('Annual Income', fmt(180000))
  row('Project Domain', 'Tailoring / Self-Employment')
  y += 2

  section('Matched NSFDC Scheme')
  row('Scheme Name', 'NSFDC Micro Finance', true)
  row('Interest Rate', `${DEFAULT_RATE}% p.a. (reducing balance)`)
  row('Max Loan Amount', fmt(140000))
  row('Moratorium Period', `${moratorium} months (interest-only)`)
  row('Subsidy Component', fmt(Math.min(principal * 0.2, 50000)))
  y += 2

  if (emiData) {
    section('EMI Projection Summary')
    row('Loan Amount Requested', fmt(principal))
    row('Total Tenure', `${tenure} months`)
    row('Moratorium EMI (Interest only)', fmt(emiData.moratorium_monthly_payment))
    row('Post-Moratorium EMI', fmt(emiData.regular_emi), true)
    row('Total Interest Payable', fmt(emiData.total_interest_paid))
    row('Total Amount Payable', fmt(emiData.total_amount_payable), true)
    y += 2
  }

  section('Selected Disbursement Branch')
  row('Branch Name', selectedBankName || 'Not selected')
  row('Routing Logic', 'Haversine GIS · NPA ≤ 8% · Active status')
  y += 2

  doc.setDrawColor(203, 213, 225)
  doc.line(PL, y, W - PL, y)
  y += 5
  doc.setFontSize(7)
  doc.setTextColor(148, 163, 184)
  doc.text('This dossier is auto-generated by UdyamSetu (NSFDC Loan Portal) for internal bank processing.', PL, y)
  y += 4
  doc.text('All figures are indicative. Final terms subject to credit assessment by the disbursing institution.', PL, y)

  doc.save('UdyamSetu_Bank_Dossier.pdf')
}

export default function CitizenDashboard() {
  const [principal,        setPrincipal]        = useState(50000)
  const [tenure,           setTenure]           = useState(24)
  const [moratorium,       setMoratorium]        = useState(3)
  const [emiData,          setEmiData]          = useState(null)
  const [selectedBank,     setSelectedBank]     = useState(null)
  const [partners,         setPartners]         = useState([])
  const [downloading,      setDownloading]      = useState(false)
  const { t } = useLanguage()

  const handleDossier = async () => {
    setDownloading(true)
    try {
      const sel = partners.find(p => p.id === selectedBank)
      await downloadDossier({
        principal, tenure, moratorium, emiData,
        selectedBankName: sel?.name ?? 'Not selected',
      })
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('citizenDashboard')}</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
            {t('dashboardDesc')}
          </p>
        </div>
        <button
          onClick={handleDossier}
          disabled={downloading}
          className="btn-primary shrink-0 gap-2 py-2.5 px-5"
        >
          {downloading
            ? <Loader2 size={15} className="animate-spin" />
            : <Download size={15} />}
          {t('downloadDossier')}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <MoratoriumVisualizer
          onEmiChange={setEmiData}
        />
        <GISMap
          selectedBank={selectedBank}
          setSelectedBank={setSelectedBank}
          onPartnersLoaded={setPartners}
        />
      </div>
    </div>
  )
}
