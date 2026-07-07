'use client'

import { RefreshCw, Server, ShieldCheck, UserRound } from 'lucide-react'
import { useAuth, getUserDisplayName } from '@/components/AuthProvider'

export function BackendStatus() {
  const { apiBaseUrl, error, isAuthenticated, loading, refresh, token, user } = useAuth()

  const status = error ? 'Backend unavailable' : loading ? 'Checking backend' : 'Backend reachable'
  const authStatus = isAuthenticated ? 'Authenticated' : 'Not signed in'

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatusTile
        icon={<Server size={18} />}
        label="Backend"
        value={apiBaseUrl}
        detail={status}
        tone={error ? 'danger' : 'primary'}
      />
      <StatusTile
        icon={<ShieldCheck size={18} />}
        label="Session"
        value={authStatus}
        detail={token ? 'Bearer token stored' : 'Cookie/session auth supported'}
        tone={isAuthenticated ? 'primary' : 'muted'}
      />
      <div className="glass-card p-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-muted-foreground">
            <UserRound size={18} />
            <p className="text-xs uppercase tracking-widest">User</p>
          </div>
          <p className="text-lg font-bold text-foreground mt-2 truncate">{getUserDisplayName(user)}</p>
          <p className="text-xs text-muted-foreground mt-1">{error ?? 'Connected through API auth'}</p>
        </div>
        <button
          onClick={() => void refresh()}
          disabled={loading}
          className="p-2 rounded-lg bg-white/5 border border-white/10 text-muted-foreground hover:text-primary hover:bg-white/10 disabled:opacity-50 transition-colors"
          aria-label="Refresh backend session"
          title="Refresh backend session"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>
    </div>
  )
}

function StatusTile({
  icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: React.ReactNode
  label: string
  value: string
  detail: string
  tone: 'primary' | 'danger' | 'muted'
}) {
  const toneClass =
    tone === 'primary'
      ? 'text-primary bg-primary/10 border-primary/20'
      : tone === 'danger'
        ? 'text-destructive bg-destructive/10 border-destructive/20'
        : 'text-muted-foreground bg-white/5 border-white/10'

  return (
    <div className="glass-card p-5 min-w-0">
      <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${toneClass}`}>
        {icon}
      </div>
      <p className="text-xs uppercase tracking-widest text-muted-foreground mt-4">{label}</p>
      <p className="text-lg font-bold text-foreground mt-1 truncate">{value}</p>
      <p className="text-xs text-muted-foreground mt-1">{detail}</p>
    </div>
  )
}
