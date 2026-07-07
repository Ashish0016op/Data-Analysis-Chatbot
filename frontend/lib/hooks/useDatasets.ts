import { useCallback, useEffect, useState } from 'react'
import { getDatasetInfo } from '@/lib/api'

export interface Dataset {
  id?: string
  name?: string
  dataset_filename?: string
  rows?: number
  total_rows?: number
  columns?: number
  total_columns?: number
  size?: string
  memory_usage_mb?: number
  createdAt?: string
  type?: string
  total_missing_values?: number
  column_details?: Array<{
    column_name: string
    dtype: string
    non_null_count: number
    null_count: number
    null_percentage: number
  }>
  [key: string]: unknown
}

interface UseDataSetsReturn {
  datasets: Dataset[]
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useDatasets(): UseDataSetsReturn {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchDatasets = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const payload = await getDatasetInfo()
      // The backend's /dataset-info/ returns a single dataset info object.
      // We wrap it in an array for consistency with the existing interface.
      if (payload && typeof payload === 'object') {
        const info = payload as Record<string, unknown>
        const dataset: Dataset = {
          id: '1',
          name: (info.dataset_filename as string) || 'Active Dataset',
          dataset_filename: info.dataset_filename as string,
          rows: info.total_rows as number,
          total_rows: info.total_rows as number,
          columns: info.total_columns as number,
          total_columns: info.total_columns as number,
          memory_usage_mb: info.memory_usage_mb as number,
          total_missing_values: info.total_missing_values as number,
          column_details: info.column_details as Dataset['column_details'],
        }
        setDatasets([dataset])
      } else {
        setDatasets([])
      }
    } catch (err) {
      setDatasets([])
      setError(err instanceof Error ? err : new Error('Failed to fetch datasets from backend'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchDatasets()
  }, [fetchDatasets])

  return { datasets, loading, error, refetch: fetchDatasets }
}
