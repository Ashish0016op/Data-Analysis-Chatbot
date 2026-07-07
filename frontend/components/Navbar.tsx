'use client'

import { Bell, HelpCircle, LogOut, RefreshCw, Search, Upload } from 'lucide-react'
import { getUserDisplayName, useAuth } from '@/components/AuthProvider'

export function Navbar() {
  const { error, isAuthenticated, loading, logout, refresh, user } = useAuth()
  const userName = getUserDisplayName(user)
  const initials =
    isAuthenticated && userName !== 'Signed in'
      ? userName
          .split(/\s+/)
          .map((part) => part[0])
          .join('')
          .slice(0, 2)
          .toUpperCase()
      : 'AI'

  return (
    <header className="h-16 bg-sidebar/40 backdrop-blur-xl border-b border-sidebar-border flex items-center justify-between px-6 md:px-8 shrink-0">
      <div className="flex-1 max-w-md relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <input
          type="text"
          placeholder="Search datasets, models, reports..."
          className="w-full pl-9 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
        />
      </div>

      <div className="flex items-center space-x-2 md:space-x-3 ml-4">
        <button
          aria-label="Help"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
        >
          <HelpCircle size={18} />
        </button>
        <button
          aria-label="Notifications"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors relative"
        >
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-accent" />
        </button>
        <button className="hidden sm:inline-flex items-center space-x-2 px-3 py-2 rounded-lg bg-primary/15 border border-primary/30 text-primary hover:bg-primary/25 transition-colors text-sm font-semibold">
          <Upload size={14} />
          <span>Upload</span>
        </button>
        <button
          onClick={() => void refresh()}
          disabled={loading}
          className={`hidden lg:inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold transition-colors ${
            error
              ? 'bg-destructive/10 border-destructive/30 text-destructive'
              : isAuthenticated
                ? 'bg-primary/10 border-primary/30 text-primary'
                : 'bg-white/5 border-white/10 text-muted-foreground hover:text-foreground'
          }`}
          title="Refresh backend session"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
        {isAuthenticated && (
          <button
            onClick={() => void logout()}
            className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-white/5 transition-colors"
            aria-label="Log out"
            title="Log out"
          >
            <LogOut size={18} />
          </button>
        )}
        <div
          className="w-9 h-9 rounded-full bg-gradient-to-br from-secondary to-primary flex items-center justify-center text-sidebar-primary-foreground font-bold text-sm"
          title={userName}
        >
          {initials}
        </div>
      </div>
    </header>
  )
}
