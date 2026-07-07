'use client'

import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { usePathname, useRouter } from 'next/navigation'
import { Sidebar } from '@/components/Sidebar'
import { Navbar } from '@/components/Navbar'
import { useAuth } from '@/components/AuthProvider'

const AUTH_ROUTES = ['/login', '/register']

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { isAuthenticated, loading } = useAuth()
  const isAuthPage = AUTH_ROUTES.includes(pathname)

  useEffect(() => {
    if (!loading && !isAuthenticated && !isAuthPage) {
      router.replace('/login')
    }
  }, [isAuthPage, isAuthenticated, loading, router])

  if (isAuthPage) {
    return <>{children}</>
  }

  if (loading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground">
        <div className="inline-flex items-center gap-3 text-sm">
          <Loader2 size={18} className="animate-spin text-primary" />
          Checking session...
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-auto bg-gradient-to-br from-background via-background to-[#0d0d10]">
          {children}
        </main>
      </div>
    </div>
  )
}
