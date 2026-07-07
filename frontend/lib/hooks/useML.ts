import { useCallback, useEffect, useState } from 'react'
import { extractArray, queryBackend } from '@/lib/api'

export interface MLModel {
  id?: string
  name?: string
  type?: string
  algorithm?: string
  accuracy?: number
  precision?: number
  recall?: number
  f1Score?: number
  trainingTime?: string
  status?: string
  [key: string]: unknown
}

interface UseMLReturn {
  models: MLModel[]
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useML(): UseMLReturn {
  const [models, setModels] = useState<MLModel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchModels = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const payload = await queryBackend(
        'List machine learning models and metrics as JSON.',
        'machine-learning',
      )
      setModels(extractArray<MLModel>(payload, ['models']))
    } catch (err) {
      setModels([])
      setError(err instanceof Error ? err : new Error('Failed to fetch ML models from backend'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchModels()
  }, [fetchModels])

  return { models, loading, error, refetch: fetchModels }
}
