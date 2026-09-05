/**
 * Apply.jsx – 3-Step Citizen Application Wizard
 */

import { useState, useRef, useCallback } from 'react'
import { matchScheme } from '../api'
import { useLanguage } from '../context/LanguageContext'
import {
  ChevronRight, ChevronLeft,
  CheckCircle2, AlertTriangle, ExternalLink, BadgePercent,
  FileCheck, Loader2, X,
} from 'lucide-react'
import {
  RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer,
} from 'recharts'

const scoreColour = (s) => {
  if (s >= 80) return '#16a34a'
  if (s >= 50) return '#d97706'
  return '#dc2626'
}

function fmt(n) {
  if (!n && n !== 0) return '—'
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${Number(n).toLocaleString('en-IN')}`
}

function StepDot({ step, current, label }) {
  const done = current > step
  const active = current === step
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all duration-300 ${done ? 'bg-green-500 border-green-500 text-white'
            : active ? 'bg-blue-700 border-blue-700 text-white shadow-lg shadow-blue-200 dark:shadow-none'
              : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 text-slate-400 dark:text-slate-500'
          }`}
      >
        {done ? <CheckCircle2 size={16} /> : step}
      </div>
      <span className={`text-[10px] font-semibold ${active ? 'text-blue-700 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500'}`}>
        {label}
      </span>
    </div>
  )
}

function StepLine({ done }) {
  return (
    <div className="flex-1 h-0.5 mx-1 mt-4 rounded transition-all duration-500 bg-slate-200 dark:bg-slate-700"
      style={{ background: done ? '#16a34a' : undefined }} />
  )
}

function Field({ label, required, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  )
}

const inputCls = `w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100
  focus:outline-none focus:ring-2 focus:ring-blue-300 dark:focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500`
const selectCls = `${inputCls} cursor-pointer`

function ScoreGauge({ score }) {
  const { t } = useLanguage()
  const colour = scoreColour(score)
  const data = [{ value: score, fill: colour }]
  return (
    <div className="relative w-44 h-44 mx-auto">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%" cy="50%"
          innerRadius="70%" outerRadius="100%"
          startAngle={90} endAngle={-270}
          data={data}
          barSize={14}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar
            background={{ fill: '#f1f5f9' }}
            dataKey="value"
            cornerRadius={8}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-3xl font-extrabold" style={{ color: colour }}>{score}</span>
        <span className="text-[10px] text-slate-500 font-medium">/ 100</span>
        <span className="text-[9px] text-slate-500 mt-0.5">{t('readinessScore')}</span>
      </div>
    </div>
  )
}

function Step1({ form, setForm, onNext }) {
  const { t } = useLanguage()

  const simulateOcr = () => {
    setForm(f => ({
      ...f,
      name: 'Rajesh Kumar',
      age: 29,
      gender: 'Male',
      category: 'SC',
      annual_income: 180000,
      has_caste_cert: true,
      has_income_cert: true,
    }))
  }

  const valid = form.name && form.age && form.gender && form.category && form.annual_income

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button onClick={simulateOcr} className="btn-outline text-xs py-1.5 flex items-center gap-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800">
          <FileCheck size={14} />
          {t('autoFillOcr') || "Simulate Document Upload"}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t('fullName')} required>
          <input className={inputCls} placeholder="e.g. Rajesh Kumar"
            value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
        </Field>
        <Field label={t('age')} required>
          <input type="number" className={inputCls} placeholder="29"
            value={form.age} onChange={e => setForm(f => ({ ...f, age: Number(e.target.value) }))} />
        </Field>
        <Field label={t('gender')} required>
          <select className={selectCls} value={form.gender}
            onChange={e => setForm(f => ({ ...f, gender: e.target.value }))}>
            <option value="">{t('select')}</option>
            {['Male', 'Female', 'Transgender', 'Other'].map(g =>
              <option key={g} value={g}>{t(g.toLowerCase())}</option>)}
          </select>
        </Field>
        <Field label={t('category')} required>
          <select className={selectCls} value={form.category}
            onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
            <option value="">{t('select')}</option>
            {['SC', 'ST', 'OBC', 'General'].map(c =>
              <option key={c} value={c}>{c === 'General' ? t('general') : c}</option>)}
          </select>
        </Field>
        <Field label={t('annualIncome')} required>
          <input type="number" className={inputCls} placeholder="180000"
            value={form.annual_income}
            onChange={e => setForm(f => ({ ...f, annual_income: Number(e.target.value) }))} />
        </Field>

      </div>

      <div className="flex justify-end">
        <button className="btn-primary" disabled={!valid} onClick={onNext}>
          {t('continueBtn')} <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}



function Step2({ form, setForm, onNext, onBack }) {
  const { t } = useLanguage()

  const valid = form.project_domain && form.requested_amount > 0

  const DOMAINS = ['Tailoring', 'Agriculture', 'Animal Husbandry', 'Education', 'Higher Studies',
    'Small Manufacturing', 'Food Processing', 'Handicrafts', 'Trade & Commerce',
    'Transport', 'Fisheries']

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">{t('businessNeedsTitle')}</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">{t('businessNeedsDesc')}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t('projectDomain')} required>
          <select className={selectCls} value={form.project_domain}
            onChange={e => setForm(f => ({ ...f, project_domain: e.target.value }))}>
            <option value="">{t('selectDomain')}</option>
            {DOMAINS.map(d => (
              <option key={d} value={d}>{t(`domain${d.replace(/ /g, '').replace(/&/g, '')}`) || d}</option>
            ))}
          </select>
        </Field>

        <Field label={t('requestedAmount')} required>
          <div className="relative">
            <input
              type="number"
              className={inputCls}
              placeholder="50000"
              value={form.requested_amount || ''}
              onChange={e => {
                const cleaned = String(e.target.value).replace(/[^0-9]/g, '')
                setForm(f => ({ ...f, requested_amount: parseInt(cleaned, 10) || '' }))
              }}
            />
          </div>
        </Field>
      </div>

      <Field label={t('tenure')}>
        <input type="number" className={inputCls} placeholder="24" min="6" max="120"
          value={form.tenure_months || ''}
          onChange={e => setForm(f => ({ ...f, tenure_months: Number(e.target.value) }))} />
      </Field>

      {form.requested_amount > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30 rounded-xl px-4 py-3 text-sm">
          <span className="text-blue-600 dark:text-blue-400">{t('reqAmountMsg')} </span>
          <span className="font-bold text-blue-800 dark:text-blue-300">{fmt(form.requested_amount)}</span>
          {form.tenure_months > 0 && (
            <span className="text-blue-500 dark:text-blue-400/80"> · {form.tenure_months} {t('month')}</span>
          )}
        </div>
      )}

      <div className="flex justify-between">
        <button className="btn-outline" onClick={onBack}>
          <ChevronLeft size={16} /> {t('backBtn')}
        </button>
        <button className="btn-primary" disabled={!valid} onClick={onNext}>
          {t('analyseBtn')} <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}

function Step3({ form, onBack }) {
  const { t } = useLanguage()
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [called, setCalled] = useState(false)

  const runMatch = async () => {
    setLoading(true); setError(null)
    try {
      const payload = {
        name: form.name,
        age: form.age,
        gender: form.gender,
        category: form.category,
        annual_income: form.annual_income,
        project_domain: form.project_domain,
        requested_amount: form.requested_amount,
        has_udyam: form.has_udyam,
        has_caste_cert: form.has_caste_cert,
        has_income_cert: form.has_income_cert,
      }
      const data = await matchScheme(payload)
      setResult(data)
      setCalled(true)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!called && !loading && !error) runMatch()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">{t('analysisTitle')}</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
          {t('analysisDescBase')} <span className="font-semibold">{form.name}</span> {t('applyingFor')} {fmt(form.requested_amount)} {t('inDomain')} <span className="font-semibold">{form.project_domain}</span>.
        </p>
      </div>

      {loading && (
        <div className="flex flex-col items-center gap-4 py-16">
          <Loader2 size={36} className="animate-spin text-blue-600 dark:text-blue-500" />
          <p className="text-sm text-slate-500 dark:text-slate-400">{t('analysing')}</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30 rounded-xl px-4 py-4 text-sm text-red-700 dark:text-red-400">
          <AlertTriangle size={16} className="inline mr-2" />
          {error}
          <button className="ml-4 btn-outline py-1 text-xs" onClick={runMatch}>{t('retry')}</button>
        </div>
      )}

      {result && !loading && (
        <>
          {!result.is_eligible ? (
            <div className="bg-red-50 dark:bg-red-900/10 border-2 border-red-300 dark:border-red-900/50 rounded-2xl px-5 py-4">
              <div className="flex items-start gap-3">
                <X size={20} className="text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                <div>
                  <p className="font-bold text-red-800 dark:text-red-300">{t('notEligible')}</p>
                  <p className="text-sm text-red-600 dark:text-red-400/80 mt-0.5">{result.ineligibility_reason}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-green-50 dark:bg-green-900/10 border border-green-300 dark:border-green-900/30 rounded-2xl px-5 py-3 flex items-center gap-3">
              <CheckCircle2 size={20} className="text-green-600 dark:text-green-500 shrink-0" />
              <p className="font-semibold text-green-800 dark:text-green-300">{t('eligibleMsg')}</p>
            </div>
          )}

          {result.is_eligible && result.matched_scheme && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="card space-y-4 border-blue-200 dark:border-blue-900/50 bg-gradient-to-br from-blue-50 to-white dark:from-slate-800 dark:to-slate-900">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-[10px] text-blue-500 font-semibold uppercase tracking-widest">{t('matchedSchemeTitle')}</p>
                      <h3 className="text-base font-bold text-blue-900 dark:text-blue-100 mt-0.5">
                        {result.matched_scheme.name}
                      </h3>
                    </div>
                    <span className="badge badge-blue">{result.matched_scheme.required_category}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-white dark:bg-slate-800 rounded-xl px-3 py-2 border border-blue-100 dark:border-slate-700">
                      <p className="text-slate-500 dark:text-slate-400">{t('maxLoan')}</p>
                      <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">{fmt(result.matched_scheme.max_amount)}</p>
                    </div>
                    <div className="bg-white dark:bg-slate-800 rounded-xl px-3 py-2 border border-blue-100 dark:border-slate-700">
                      <p className="text-slate-500 dark:text-slate-400">{t('interestRate')}</p>
                      <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">{result.matched_scheme.base_interest_rate}% p.a.</p>
                    </div>
                    <div className="bg-white dark:bg-slate-800 rounded-xl px-3 py-2 border border-blue-100 dark:border-slate-700">
                      <p className="text-slate-500 dark:text-slate-400">{t('moratoriumText')}</p>
                      <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                        {result.matched_scheme.min_moratorium_months === result.matched_scheme.max_moratorium_months
                          ? `${result.matched_scheme.min_moratorium_months} months`
                          : `${result.matched_scheme.min_moratorium_months}–${result.matched_scheme.max_moratorium_months} months`}
                      </p>
                    </div>
                    <div className="bg-white dark:bg-slate-800 rounded-xl px-3 py-2 border border-green-100 dark:border-green-900/30 bg-green-50 dark:bg-green-900/10">
                      <p className="text-slate-500 dark:text-slate-400 flex items-center gap-1"><BadgePercent size={11} /> {t('subsidyText')}</p>
                      <p className="font-bold text-green-700 dark:text-green-400 mt-0.5">{fmt(result.subsidy_amount)}</p>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    {result.matched_scheme.description}
                  </p>
                </div>

                <div className="card flex flex-col items-center justify-center gap-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t('readinessScore')}</p>
                  <ScoreGauge score={result.readiness_score} />
                </div>
              </div>

              {result.gaps.length > 0 && (
                <div className="rounded-2xl border-2 border-yellow-300 dark:border-yellow-700/50 bg-yellow-50 dark:bg-yellow-900/10 px-5 py-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={18} className="text-yellow-600 dark:text-yellow-500 shrink-0" />
                    <p className="font-bold text-yellow-800 dark:text-yellow-300">{t('actionItemsTitle')}</p>
                  </div>
                  <ol className="space-y-2">
                    {result.gaps.map((gap, i) => {
                      const urlMatch = gap.match(/https?:\/\/[^\s]+/)
                      const url = urlMatch?.[0]
                      const text = url ? gap.replace(url, '').trim() : gap
                      return (
                        <li key={i} className="flex items-start gap-3">
                          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-yellow-400 dark:bg-yellow-600 text-yellow-900 dark:text-yellow-100 text-[10px] font-bold flex items-center justify-center mt-0.5">
                            {i + 1}
                          </span>
                          <div className="text-sm text-yellow-900 dark:text-yellow-400/80 leading-snug">
                            {text}
                            {url && (
                              <a href={url} target="_blank" rel="noopener noreferrer"
                                className="ml-2 inline-flex items-center gap-0.5 text-blue-600 dark:text-blue-400 font-semibold hover:underline text-xs">
                                Register <ExternalLink size={11} />
                              </a>
                            )}
                          </div>
                        </li>
                      )
                    })}
                  </ol>
                </div>
              )}

              {result.gaps.length === 0 && (
                <div className="rounded-2xl border border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-900/20 px-5 py-4 flex items-center gap-3">
                  <CheckCircle2 size={18} className="text-green-600 dark:text-green-500 shrink-0" />
                  <p className="text-sm font-semibold text-green-800 dark:text-green-300">
                    {t('allDocsOrder')}
                  </p>
                </div>
              )}


            </>
          )}
        </>
      )}

      <div className="flex justify-between pt-2">
        <button className="btn-outline" onClick={onBack}>
          <ChevronLeft size={16} /> {t('backBtn')}
        </button>
        <button className="btn-outline" onClick={runMatch} disabled={loading}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : null}
          {t('reAnalyseBtn')}
        </button>
      </div>
    </div>
  )
}

const EMPTY_FORM = {
  name: '', age: '', gender: '', category: '',
  annual_income: '', lat: '', lng: '',
  has_udyam: false, has_caste_cert: false, has_income_cert: false,
  project_domain: '', requested_amount: '', tenure_months: 24,
}

export default function Apply() {
  const { t } = useLanguage()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(EMPTY_FORM)

  const STEPS = [
    { label: t('stepProfile') },
    { label: t('stepBusiness') },
    { label: t('stepAnalysis') },
  ]

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('applyHeader')}</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
          {t('applyDesc')}
        </p>
      </div>

      <div className="flex items-start">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-start flex-1">
            <div className="flex flex-col items-center w-full">
              <StepDot step={i + 1} current={step} label={s.label} />
            </div>
            {i < STEPS.length - 1 && <StepLine done={step > i + 1} />}
          </div>
        ))}
      </div>

      <div className="card min-h-[420px]">
        {step === 1 && <Step1 form={form} setForm={setForm} onNext={() => setStep(2)} />}
        {step === 2 && <Step2 form={form} setForm={setForm} onNext={() => setStep(3)} onBack={() => setStep(1)} />}
        {step === 3 && <Step3 form={form} onBack={() => setStep(2)} />}
      </div>
    </div>
  )
}
