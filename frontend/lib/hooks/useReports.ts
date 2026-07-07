'use client'

import { useEffect, useState } from 'react'
import { extractArray, queryBackend } from '@/lib/api'

export interface ReportSummary {
  [key: string]: unknown
}

export interface ReportItem {
  id?: string
  name?: string
  type?: string
  createdAt?: string
  status?: string
  size?: string
  [key: string]: unknown
}

export function useReports() {
  const [summary, setSummary] = useState<ReportSummary | null>(null)
  const [reports, setReports] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchReports() {
      setLoading(true)
      setError(null)

      try {
        const payload = await queryBackend(
          'Return report summary and saved reports as JSON.',
          'reports',
        )
        if (cancelled) return

        setSummary(payload && typeof payload === 'object' ? (payload as ReportSummary) : { result: payload })
        setReports(extractArray<ReportItem>(payload, ['reports']))
      } catch (err) {
        if (!cancelled) {
          setSummary(null)
          setReports([])
          setError(err instanceof Error ? err.message : 'Failed to fetch reports from backend')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchReports()

    return () => {
      cancelled = true
    }
  }, [])

  return { summary, reports, loading, error }
}
