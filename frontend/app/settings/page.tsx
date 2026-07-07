'use client'

import { LogOut, RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { AnalyticsCard } from '@/components/CardComponents'
import { BackendStatus } from '@/components/BackendStatus'
import { getUserDisplayName, useAuth } from '@/components/AuthProvider'

export default function Settings() {
  const { error, isAuthenticated, loading, logout, refresh, user } = useAuth()

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-5xl">
      <PageHeader
        badge="Session"
        title="Settings"
        description="Manage your backend session and account preferences."
        actions={
          <button
            onClick={() => void refresh()}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-white/5 border border-white/10 text-sm font-semibold text-foreground hover:bg-white/10 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh Session
          </button>
        }
      />

      <BackendStatus />

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <AnalyticsCard
        title={isAuthenticated ? 'Active Session' : 'Session Status'}
        subtitle={
          isAuthenticated
            ? `You are signed in as ${getUserDisplayName(user)}.`
            : 'Sign in from the login page to access protected backend endpoints.'
        }
      >
        {isAuthenticated ? (
          <div className="space-y-4">
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-widest text-muted-foreground">Authenticated User</p>
              <p className="text-lg font-bold text-foreground mt-1">{getUserDisplayName(user)}</p>
              {user && (
                <pre className="mt-3 max-h-48 overflow-auto text-xs text-muted-foreground bg-black/20 rounded p-3">
                  {JSON.stringify(user, null, 2)}
                </pre>
              )}
            </div>
            <button
              onClick={() => void logout()}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-destructive/15 border border-destructive/30 px-4 py-2 text-sm font-semibold text-destructive hover:bg-destructive/25 disabled:opacity-50 transition-colors"
            >
              <LogOut size={15} />
              Sign Out
            </button>
          </div>
        ) : (
          <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-center">
            <p className="text-sm text-muted-foreground">
              You are not currently signed in. Visit the{' '}
              <a href="/login" className="text-primary hover:underline font-medium">
                login page
              </a>{' '}
              to authenticate with the backend.
            </p>
          </div>
        )}
      </AnalyticsCard>
    </div>
  )
}