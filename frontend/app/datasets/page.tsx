'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Database,
  Eye,
  FileSpreadsheet,
  HardDrive,
  Hash,
  Loader2,
  Search,
  Table2,
} from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { BackendResponse } from '@/components/BackendResponse'
import { getDatasetInfo, queryBackend } from '@/lib/api'

interface ColumnDetail {
  column_name: string
  dtype: string
  schema_type?: string
  description?: string
  non_null_count: number
  null_count: number
  null_percentage: number
  unique_values: number
  sample_values?: string[]
}

interface DatasetInfo {
  total_datasets: number
  dataset_filename: string
  total_rows: number
  total_columns: number
  column_details: ColumnDetail[]
  total_missing_values: number
  memory_usage_mb: number
}

function formatNumber(value: number | string) {
  const number = typeof value === 'string' ? Number(value) : value
  if (!Number.isFinite(number)) return String(value)
  if (number >= 1_000_000) return `${(number / 1_000_000).toFixed(1)}M`
  if (number >= 1_000) return `${(number / 1_000).toFixed(1)}K`
  return number.toLocaleString()
}

function getTypeTone(dtype: string) {
  const lower = dtype.toLowerCase()
  if (lower.includes('int') || lower.includes('float') || lower.includes('double')) {
    return 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
  }
  if (lower.includes('date') || lower.includes('time')) {
    return 'border-amber-400/20 bg-amber-400/10 text-amber-300'
  }
  return 'border-primary/20 bg-primary/10 text-primary'
}

export default function Datasets() {
  const [queryInput, setQueryInput] = useState('')
  const [resultPayload, setResultPayload] = useState<unknown | null>(null)
  const [queryLoading, setQueryLoading] = useState(false)
  const [datasetLoading, setDatasetLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [datasetError, setDatasetError] = useState<string | null>(null)
  const [datasetInfo, setDatasetInfo] = useState<DatasetInfo | null>(null)
  const [columnFilter, setColumnFilter] = useState('')

  useEffect(() => {
    async function fetchInfo() {
      try {
        setDatasetLoading(true)
        setDatasetError(null)
        const payload = await getDatasetInfo()
        setDatasetInfo(payload as DatasetInfo)
      } catch (err) {
        setDatasetError(err instanceof Error ? err.message : 'Failed to load dataset info')
      } finally {
        setDatasetLoading(false)
      }
    }

    void fetchInfo()
    window.addEventListener('dataset-uploaded', fetchInfo)
    return () => window.removeEventListener('dataset-uploaded', fetchInfo)
  }, [])

  const filteredColumns = useMemo(() => {
    const filter = columnFilter.trim().toLowerCase()
    if (!datasetInfo) return []
    if (!filter) return datasetInfo.column_details
    return datasetInfo.column_details.filter((column) =>
      `${column.column_name} ${column.dtype}`.toLowerCase().includes(filter),
    )
  }, [columnFilter, datasetInfo])

  const numericColumnCount = useMemo(() => {
    if (!datasetInfo) return 0
    return datasetInfo.column_details.filter((column) => {
      const dtype = column.dtype.toLowerCase()
      return dtype.includes('int') || dtype.includes('float') || dtype.includes('double')
    }).length
  }, [datasetInfo])

  const handleQuery = async () => {
    if (!queryInput.trim() || queryLoading) return
    setQueryLoading(true)
    setError(null)
    setResultPayload(null)

    try {
      const payload = await queryBackend(queryInput, 'datasets')
      setResultPayload(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed')
    } finally {
      setQueryLoading(false)
    }
  }

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl">
      <PageHeader
        badge="Data Assets"
        title="Datasets"
        description="Inspect your active dataset, review schema details, and ask focused questions."
      />

      {datasetError && (
        <StatusMessage tone="error" message={datasetError} />
      )}

      {datasetLoading ? (
        <div className="glass-card p-6 flex items-center gap-3 text-sm text-muted-foreground">
          <Loader2 size={18} className="animate-spin text-primary" />
          Loading dataset metadata...
        </div>
      ) : datasetInfo ? (
        <>
          <div className="glass-card p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                  <FileSpreadsheet size={13} />
                  Active dataset
                </div>
                <h2 className="mt-3 truncate text-xl font-bold text-foreground">
                  {datasetInfo.dataset_filename}
                </h2>
                <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                  Dataset metadata is loaded from the backend and refreshed from the active CSV.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[560px]">
                <Metric icon={<Table2 size={16} />} label="Rows" value={formatNumber(datasetInfo.total_rows)} />
                <Metric icon={<Database size={16} />} label="Columns" value={formatNumber(datasetInfo.total_columns)} />
                <Metric icon={<Hash size={16} />} label="Numeric" value={formatNumber(numericColumnCount)} />
                <Metric icon={<HardDrive size={16} />} label="Memory" value={`${datasetInfo.memory_usage_mb.toFixed(1)} MB`} />
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <section className="glass-card overflow-hidden">
              <div className="flex flex-col gap-3 border-b border-white/10 p-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Schema</h2>
                  <p className="text-xs text-muted-foreground">
                    {filteredColumns.length} of {datasetInfo.column_details.length} columns
                  </p>
                </div>
                <div className="relative w-full md:w-72">
                  <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input
                    value={columnFilter}
                    onChange={(event) => setColumnFilter(event.target.value)}
                    placeholder="Filter columns or types"
                    className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
                  />
                </div>
              </div>

              <div className="max-h-[540px] overflow-auto">
                <table className="w-full min-w-[940px] text-left text-xs">
                  <thead className="sticky top-0 z-10 border-b border-white/10 bg-sidebar text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 font-medium">Column</th>
                      <th className="px-4 py-3 font-medium">Type</th>
                      <th className="px-4 py-3 font-medium">Description</th>
                      <th className="px-4 py-3 text-right font-medium">Non-null</th>
                      <th className="px-4 py-3 text-right font-medium">Nulls</th>
                      <th className="px-4 py-3 text-right font-medium">Unique</th>
                      <th className="px-4 py-3 font-medium">Sample</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filteredColumns.map((column) => (
                      <tr key={column.column_name} className="hover:bg-white/[0.03]">
                        <td className="px-4 py-3 font-medium text-foreground">{column.column_name}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full border px-2 py-1 font-mono text-[11px] ${getTypeTone(column.dtype)}`}>
                            {column.schema_type || column.dtype}
                          </span>
                        </td>
                        <td className="max-w-[320px] px-4 py-3 text-muted-foreground">
                          <span className="line-clamp-2">{column.description || 'No description'}</span>
                        </td>
                        <td className="px-4 py-3 text-right text-foreground">{formatNumber(column.non_null_count)}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={column.null_count > 0 ? 'text-amber-300' : 'text-muted-foreground'}>
                            {formatNumber(column.null_count)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-foreground">{formatNumber(column.unique_values)}</td>
                        <td className="max-w-[260px] truncate px-4 py-3 text-muted-foreground">
                          {column.sample_values?.slice(0, 3).join(', ') || 'No sample'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <aside className="space-y-4">
              <div className="glass-card p-4">
                <h2 className="text-sm font-semibold text-foreground">Quick Questions</h2>
                <div className="mt-3 space-y-2">
                  <PromptButton label="Preview rows" prompt="Show me the first 20 rows of the active dataset" onSelect={setQueryInput} icon={<Eye size={14} />} />
                  <PromptButton label="Schema summary" prompt="Summarize the active dataset schema by data type" onSelect={setQueryInput} icon={<Database size={14} />} />
                  <PromptButton label="Missing values" prompt="Which columns have missing values and what are their percentages?" onSelect={setQueryInput} icon={<AlertCircle size={14} />} />
                </div>
              </div>

              <div className="glass-card p-4">
                <h2 className="text-sm font-semibold text-foreground">Data Quality</h2>
                <div className="mt-3 rounded-lg border border-white/10 bg-white/5 p-3">
                  <p className="text-xs uppercase tracking-widest text-muted-foreground">Missing values</p>
                  <p className="mt-1 text-2xl font-bold text-foreground">{formatNumber(datasetInfo.total_missing_values)}</p>
                </div>
              </div>
            </aside>
          </div>
        </>
      ) : null}

      <section className="glass-card p-5">
        <div className="flex items-center gap-2">
          <Search size={16} className="text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Ask About This Dataset</h2>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={queryInput}
            onChange={(event) => setQueryInput(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && handleQuery()}
            placeholder="Ask about rows, schema, missing values, or summaries"
            className="min-h-11 flex-1 rounded-lg border border-white/10 bg-white/5 px-4 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
          />
          <button
            onClick={handleQuery}
            disabled={queryLoading || !queryInput.trim()}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-primary/30 bg-primary/15 px-5 text-sm font-semibold text-primary transition-colors hover:bg-primary/25 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {queryLoading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Query
          </button>
        </div>

        {error && (
          <StatusMessage tone="error" message={error} className="mt-4" />
        )}

        {resultPayload !== null && (
          <div className="mt-5 rounded-lg border border-white/10 bg-black/20 p-4">
            <BackendResponse payload={resultPayload} />
          </div>
        )}
      </section>
    </div>
  )
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <span className="text-[11px] uppercase tracking-widest">{label}</span>
      </div>
      <p className="mt-2 text-lg font-bold text-foreground">{value}</p>
    </div>
  )
}

function PromptButton({
  icon,
  label,
  prompt,
  onSelect,
}: {
  icon: React.ReactNode
  label: string
  prompt: string
  onSelect: (prompt: string) => void
}) {
  return (
    <button
      onClick={() => onSelect(prompt)}
      className="flex w-full items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-left text-sm text-foreground transition-colors hover:border-primary/30 hover:bg-primary/10"
    >
      <span className="text-primary">{icon}</span>
      <span className="truncate">{label}</span>
    </button>
  )
}

function StatusMessage({
  message,
  tone,
  className = '',
}: {
  message: string
  tone: 'error'
  className?: string
}) {
  return (
    <div className={`rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2 ${className}`}>
      <AlertCircle size={14} />
      <span>{message}</span>
    </div>
  )
}
