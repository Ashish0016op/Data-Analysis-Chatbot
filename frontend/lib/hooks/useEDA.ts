import { useEffect, useState } from 'react'
import { queryBackend } from '@/lib/api'

export interface EDAData {
  [key: string]: unknown
}

interface UseEDAReturn {
  data: EDAData | null
  loading: boolean
  error: Error | null
}

export function useEDA(datasetId: string): UseEDAReturn {
  const [data, setData] = useState<EDAData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchEDA() {
      setLoading(true)
      setError(null)

      try {
        const payload = await queryBackend(
          `Run exploratory data analysis for dataset ${datasetId} and return the result as JSON.`,
          'eda',
        )
        if (!cancelled) setData(payload && typeof payload === 'object' ? (payload as EDAData) : { result: payload })
      } catch (err) {
        if (!cancelled) {
          setData(null)
          setError(err instanceof Error ? err : new Error('Failed to fetch EDA data from backend'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchEDA()

    return () => {
      cancelled = true
    }
  }, [datasetId])

  return { data, loading, error }
}
