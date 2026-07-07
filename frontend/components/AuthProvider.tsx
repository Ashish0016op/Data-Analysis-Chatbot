'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  API_BASE_URL,
  ApiError,
  getCurrentUser,
  getStoredToken,
  login as backendLogin,
  logout as backendLogout,
  setStoredToken,
} from '@/lib/api'

type BackendUser = Record<string, unknown>

interface AuthContextValue {
  apiBaseUrl: string
  user: BackendUser | null
  token: string | null
  loading: boolean
  error: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function normalizeUser(payload: unknown): BackendUser | null {
  if (!payload || typeof payload !== 'object') return null
  const data = payload as Record<string, unknown>

  for (const key of ['user', 'profile', 'account', 'data']) {
    const value = data[key]
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as BackendUser
    }
  }

  return data
}

function shouldHideAuthError(error: unknown) {
  return error instanceof ApiError && [401, 403, 404].includes(error.status ?? 0)
}

function isAuthFailure(error: unknown) {
  return error instanceof ApiError && [401, 403].includes(error.status ?? 0)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<BackendUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    setToken(getStoredToken())

    try {
      const payload = await getCurrentUser()
      setUser(normalizeUser(payload))
    } catch (err) {
      setUser(null)
      if (isAuthFailure(err)) {
        setStoredToken(null)
      }
      if (!shouldHideAuthError(err)) {
        setError(err instanceof Error ? err.message : 'Unable to reach backend.')
      }
    } finally {
      setToken(getStoredToken())
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()

    const updateToken = () => {
      const storedToken = getStoredToken()
      setToken(storedToken)
      if (!storedToken) {
        setUser(null)
      }
    }
    window.addEventListener('backend-auth-change', updateToken)
    window.addEventListener('storage', updateToken)

    return () => {
      window.removeEventListener('backend-auth-change', updateToken)
      window.removeEventListener('storage', updateToken)
    }
  }, [refresh])

  const login = useCallback(
    async (email: string, password: string) => {
      setLoading(true)
      setError(null)

      try {
        const payload = await backendLogin(email, password)
        setToken(getStoredToken())
        setUser(normalizeUser(payload))
        await refresh()
      } catch (err) {
        setUser(null)
        setError(err instanceof Error ? err.message : 'Login failed.')
        throw err
      } finally {
        setLoading(false)
      }
    },
    [refresh],
  )

  const logout = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      await backendLogout()
    } finally {
      setUser(null)
      setToken(null)
      setLoading(false)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      apiBaseUrl: API_BASE_URL,
      user,
      token,
      loading,
      error,
      isAuthenticated: Boolean(user || token),
      login,
      logout,
      refresh,
    }),
    [error, loading, login, logout, refresh, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}

export function getUserDisplayName(user: BackendUser | null) {
  if (!user) return 'Not signed in'

  const value =
    user.email ??
    user.username ??
    user.name ??
    user.full_name ??
    user.sub ??
    user.id ??
    'Signed in'

  return String(value)
}
