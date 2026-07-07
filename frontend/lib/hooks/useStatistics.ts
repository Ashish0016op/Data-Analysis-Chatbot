import { useEffect, useState } from 'react'
import { queryBackend } from '@/lib/api'

export interface StatisticsData {
  [key: string]: unknown
}

interface UseStatisticsReturn {
  data: StatisticsData | null
  loading: boolean
  error: Error | null
}

export function useStatistics(datasetId: string): UseStatisticsReturn {
  const [data, setData] = useState<StatisticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchStatistics() {
      setLoading(true)
      setError(null)

      try {
        const payload = await queryBackend(
          `Run statistical analysis for dataset ${datasetId} and return descriptive statistics, tests, and correlations as JSON.`,
          'statistics',
        )
        if (!cancelled) {
          setData(payload && typeof payload === 'object' ? (payload as StatisticsData) : { result: payload })
        }
      } catch (err) {
        if (!cancelled) {
          setData(null)
          setError(err instanceof Error ? err : new Error('Failed to fetch statistics from backend'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchStatistics()

    return () => {
      cancelled = true
    }
  }, [datasetId])

  return { data, loading, error }
}
