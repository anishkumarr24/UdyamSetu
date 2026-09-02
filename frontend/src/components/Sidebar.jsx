import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, BookOpen, Building2, FileText, Wand2, ShieldAlert, Globe, Sun, Moon, LogIn, LogOut, UserCircle } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'
import LoginModal from './LoginModal'

const links = [
  { to: '/',              icon: LayoutDashboard, labelKey: 'dashboard'    },
  { to: '/schemes',       icon: BookOpen,         labelKey: 'schemes'      },
  { to: '/partners',      icon: Building2,        labelKey: 'partners'     },
  { to: '/users',         icon: Users,            labelKey: 'beneficiaries'},
  { to: '/applications',  icon: FileText,         labelKey: 'applications' },
  { to: '/admin/bank',    icon: ShieldAlert,      labelKey: 'adminPortal' },
]

const ctaLink = { to: '/apply', icon: Wand2, labelKey: 'applyNow' }

export default function Sidebar() {
  const { language, toggleLanguage, t } = useLanguage()
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()
  const [isLoginOpen, setIsLoginOpen] = useState(false)

  // Filter links based on role
  const visibleLinks = links.filter(link => {
    if (link.to.startsWith('/admin')) {
      return user && user.role === 'bank_admin'
    }
    return true
  })

  return (
    <aside className="fixed inset-y-0 left-0 w-60 bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 flex flex-col z-20 transition-colors">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-200 dark:border-slate-800">
        <div className="w-8 h-8 rounded-lg bg-blue-700 flex items-center justify-center">
          <span className="text-white font-bold text-sm">US</span>
        </div>
        <div>
          <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight">UdyamSetu</p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">NSFDC Loan Portal</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {visibleLinks.map(({ to, icon: Icon, labelKey }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors duration-100 ${
                isActive
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                  : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
              }`
            }
          >
            <Icon size={17} />
            {t(labelKey)}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 pb-4 pt-2 border-t border-slate-200 dark:border-slate-800">
        {/* Apply CTA */}
        <NavLink
          to={ctaLink.to}
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold mb-4 transition-colors duration-100 ${
              isActive
                ? 'bg-blue-700 text-white'
                : 'bg-blue-700 text-white hover:bg-blue-800'
            }`
          }
        >
          <ctaLink.icon size={17} />
          {t(ctaLink.labelKey)}
          <span className="ml-auto text-[9px] bg-white/20 px-1.5 py-0.5 rounded-full">NEW</span>
        </NavLink>
        
        {/* Auth Section */}
        {user ? (
          <div className="mb-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl p-3 border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-3">
              <UserCircle className="text-slate-400" size={24} />
              <div className="overflow-hidden">
                <p className="text-sm font-bold text-slate-700 dark:text-slate-200 truncate">{user.name}</p>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">{user.role}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="w-full flex items-center justify-center gap-2 py-1.5 text-xs font-semibold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <LogOut size={14} />
              Sign Out
            </button>
          </div>
        ) : (
          <button
            onClick={() => setIsLoginOpen(true)}
            className="w-full mb-4 flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <LogIn size={17} />
            Sign In / Register
          </button>
        )}
        
        <LoginModal isOpen={isLoginOpen} onClose={() => setIsLoginOpen(false)} />
        <div className="flex gap-2 mb-3">
          <button 
            onClick={toggleLanguage}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            title={t('language')}
          >
            <Globe size={14} className="text-slate-500 dark:text-slate-400" />
            <span>{language === 'en' ? 'EN' : 'HI'}</span>
          </button>
          
          <button 
            onClick={toggleTheme}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            title={t('theme')}
          >
            {theme === 'dark' ? <Moon size={14} className="text-slate-400" /> : <Sun size={14} className="text-amber-500" />}
          </button>
        </div>

        <p className="text-[10px] text-slate-400 dark:text-slate-500 px-3 text-center">© 2024 NSFDC · UdyamSetu v1.0</p>
      </div>
    </aside>
  )
}
