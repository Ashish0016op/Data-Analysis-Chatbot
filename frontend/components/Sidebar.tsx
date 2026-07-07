'use client'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { LayoutDashboard, Database, Search, BarChart3, LineChart, Brain, MessageSquare, FileText, Settings, Sparkles, UserCircle, LogOut } from 'lucide-react'
import { usePathname } from 'next/navigation'
import { useAuth, getUserDisplayName } from '@/components/AuthProvider'

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Datasets', path: '/datasets', icon: Database },
  { name: 'EDA Analysis', path: '/eda', icon: Search },
  { name: 'Visualizations', path: '/visualizations', icon: BarChart3 },
  { name: 'Statistics', path: '/statistics', icon: LineChart },
  { name: 'ML Studio', path: '/ml', icon: Brain },
  { name: 'AI Assistant', path: '/ai-assistant', icon: MessageSquare },
  { name: 'Reports', path: '/reports', icon: FileText },
  { name: 'Settings', path: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { error, loading, logout, user } = useAuth()

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border hidden md:flex flex-col py-6 px-4">
      <Link href="/" className="flex items-center space-x-2 px-3 mb-8">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg shadow-primary/30">
          <Sparkles size={18} className="text-background" />
        </div>
        <div className="flex flex-col">
          <span className="text-base font-bold glow-text leading-none">Insightly</span>
          <span className="text-[10px] text-muted-foreground tracking-widest uppercase">Analytics</span>
        </div>
      </Link>

      <nav className="flex-1 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const active =
            item.path === '/'
              ? pathname === '/'
              : pathname.startsWith(item.path)
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`group relative flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-sidebar-foreground hover:bg-white/5 hover:text-foreground'
              }`}
            >
              {active && (
                <motion.span
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-r-full bg-primary"
                />
              )}
              <Icon size={18} className={active ? 'text-primary' : 'opacity-70'} />
              <span className="text-sm font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}