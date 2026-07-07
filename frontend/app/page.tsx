'use client'

import { useEffect, useState } from 'react'
import {
  Database, Table2, BarChart3, FileSpreadsheet, Loader2, AlertCircle,
  ChevronDown, ChevronRight, Search, FileText, Layers, HardDrive,
  Clock, TrendingUp, Hash, AlertTriangle, Eye
} from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { getDatasetInfo } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'

interface ColumnDetail {
  column_name: string
  dtype: string
  non_null_count: number
  null_count: number
  null_percentage: number
  unique_values: number
  sample_values?: string[]
  min?: number
  max?: number
  mean?: number
  median?: number
  std?: number
}

interface DatasetInfo {
  total_datasets: number
  dataset_filename: string
  total_rows: number
  total_columns: number
  column_details: ColumnDetail[]
  missing_values: Record<string, number>
  sample_data: Record<string, unknown>[]
  total_missing_values: number
  memory_usage_mb: number
  [key: string]: unknown
}

function formatNumber(n: number | string): string {
  const num = typeof n === 'string' ? Number(n) : n
  if (isNaN(num)) return String(n)
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return num.toLocaleString()
}

function getDtypeColor(dtype: string): string {
  if (dtype.includes('int')) return 'text-blue-400'
  if (dtype.includes('float') || dtype.includes('double')) return 'text-emerald-400'
  if (dtype.includes('datetime')) return 'text-amber-400'
  if (dtype.includes('string') || dtype.includes('object')) return 'text-violet-400'
  return 'text-muted-foreground'
}

export default function Dashboard() {
  const [info, setInfo] = useState<DatasetInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedColumns, setExpandedColumns] = useState(false)
  const [expandedSample, setExpandedSample] = useState(false)

  useEffect(() => {
    async function fetch() {
      try {
        setLoading(true)
        setError(null)
        const data = await getDatasetInfo()
        setInfo(data as DatasetInfo)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch dataset info')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  if (loading) {
    return (
      <div className="p-6 md:p-8 space-y-8">
        <PageHeader badge="Dataset Overview" title="Dashboard" description="Loading dataset information..." />
        <div className="flex items-center justify-center py-20">
          <Loader2 size={28} className="animate-spin text-primary" />
          <span className="ml-3 text-sm text-muted-foreground">Loading dataset information...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 md:p-8 space-y-8">
        <PageHeader badge="Dataset Overview" title="Dashboard" description="View and manage your datasets." />
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-5 py-4 text-sm text-destructive flex items-start gap-3">
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Unable to load dataset info</p>
            <p className="text-destructive/80 mt-0.5">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!info) return null

  const numericCols = info.column_details.filter(c => c.dtype.includes('int') || c.dtype.includes('float') || c.dtype.includes('double'))
  const highNullCols = info.column_details.filter(c => c.null_percentage > 0).sort((a, b) => b.null_percentage - a.null_percentage)

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl">
      <PageHeader
        badge={info.dataset_filename}
        title="Dashboard"
        description="Real-time dataset metrics and column-level analysis."
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard icon={<Database size={18} />} label="Datasets" value={String(info.total_datasets)} detail="Connected" />
        <KpiCard icon={<Table2 size={18} />} label="Total Rows" value={formatNumber(info.total_rows)} detail="Records" />
        <KpiCard icon={<Layers size={18} />} label="Columns" value={String(info.total_columns)} detail="Features" />
        <KpiCard icon={<Hash size={18} />} label="Numeric" value={String(numericCols.length)} detail="Columns" />
        <KpiCard icon={<AlertTriangle size={18} />} label="Missing" value={formatNumber(info.total_missing_values)} detail="Values" />
        <KpiCard icon={<HardDrive size={18} />} label="Memory" value={`${info.memory_usage_mb.toFixed(1)}`} detail="MB" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Column Details Table */}
        <div className="lg:col-span-2 glass-card overflow-hidden">
          <button
            onClick={() => setExpandedColumns(!expandedColumns)}
            className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Search size={16} className="text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Column Details ({info.column_details.length})</h2>
            </div>
            {expandedColumns ? <ChevronDown size={16} className="text-muted-foreground" /> : <ChevronRight size={16} className="text-muted-foreground" />}
          </button>

          {expandedColumns && (
            <div className="overflow-x-auto border-t border-white/5">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-white/5 text-muted-foreground uppercase tracking-wider">
                    <th className="text-left p-3 font-medium">Column</th>
                    <th className="text-left p-3 font-medium">Type</th>
                    <th className="text-right p-3 font-medium">Non-Null</th>
                    <th className="text-right p-3 font-medium">Null %</th>
                    <th className="text-right p-3 font-medium">Unique</th>
                    <th className="text-left p-3 font-medium">Sample Values</th>
                  </tr>
                </thead>
                <tbody>
                  {info.column_details.map((col, i) => (
                    <tr key={col.column_name} className="border-t border-white/5 hover:bg-white/5 transition-colors">
                      <td className="p-3 text-foreground font-medium whitespace-nowrap">{col.column_name}</td>
                      <td className={`p-3 ${getDtypeColor(col.dtype)} whitespace-nowrap font-mono`}>{col.dtype}</td>
                      <td className="p-3 text-right text-foreground">{formatNumber(col.non_null_count)}</td>
                      <td className={`p-3 text-right ${col.null_percentage > 50 ? 'text-destructive' : col.null_percentage > 0 ? 'text-amber-400' : 'text-muted-foreground'}`}>
                        {col.null_percentage.toFixed(1)}%
                      </td>
                      <td className="p-3 text-right text-foreground">{formatNumber(col.unique_values)}</td>
                      <td className="p-3 text-muted-foreground max-w-[200px] truncate">
                        {col.sample_values?.slice(0, 3).join(', ') || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Side Panel */}
        <div className="space-y-4">
          {/* Data Quality Summary */}
          <div className="glass-card p-4">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-3">
              <AlertTriangle size={14} className="text-amber-400" />
              Data Quality
            </h3>
            <div className="space-y-2">
              {highNullCols.length > 0 ? (
                highNullCols.slice(0, 5).map(col => (
                  <div key={col.column_name} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground truncate mr-2">{col.column_name}</span>
                    <span className="text-destructive font-medium">{col.null_percentage.toFixed(1)}% null</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">No missing values detected</p>
              )}
              {highNullCols.length > 5 && (
                <p className="text-xs text-muted-foreground">+{highNullCols.length - 5} more columns with nulls</p>
              )}
            </div>
          </div>

          {/* Numeric Stats Summary */}
          {numericCols.length > 0 && (
            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-3">
                <TrendingUp size={14} className="text-emerald-400" />
                Numeric Columns
              </h3>
              <div className="space-y-2">
                {numericCols.slice(0, 6).map(col => (
                  <div key={col.column_name} className="text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground truncate mr-2">{col.column_name}</span>
                      <span className="text-foreground font-medium">
                        {col.mean !== undefined ? formatNumber(col.mean) : '—'} avg
                      </span>
                    </div>
                    {col.min !== undefined && col.max !== undefined && (
                      <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
                        <span>Min: {formatNumber(col.min)}</span>
                        <span>Max: {formatNumber(col.max)}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sample Data */}
          {info.sample_data.length > 0 && (
            <div className="glass-card overflow-hidden">
              <button
                onClick={() => setExpandedSample(!expandedSample)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Eye size={14} className="text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Sample Data</h3>
                </div>
                {expandedSample ? <ChevronDown size={14} className="text-muted-foreground" /> : <ChevronRight size={14} className="text-muted-foreground" />}
              </button>
              {expandedSample && (
                <div className="overflow-x-auto border-t border-white/5 max-h-80 overflow-y-auto">
                  <table className="w-full text-[10px]">
                    <thead className="sticky top-0 bg-sidebar">
                      <tr className="text-muted-foreground uppercase tracking-wider">
                        {Object.keys(info.sample_data[0]).slice(0, 8).map(key => (
                          <th key={key} className="text-left p-2 font-medium whitespace-nowrap">{key.replace(/^[^\x20-\x7E]/, '').slice(0, 15)}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {info.sample_data.map((row, i) => (
                        <tr key={i} className="border-t border-white/5">
                          {Object.entries(row).slice(0, 8).map(([key, val]) => (
                            <td key={key} className="p-2 text-muted-foreground truncate max-w-[120px]">
                              {val === null || val === 'NaT' || val === '<NA>' ? '—' : String(val).trim()}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail: string }) {
  return (
    <div className="glass-card p-4 group hover:border-primary/20 transition-all duration-300">
      <div className="w-9 h-9 rounded-xl border border-white/10 bg-white/5 flex items-center justify-center text-muted-foreground mb-2 group-hover:bg-primary/10 group-hover:border-primary/30 group-hover:text-primary transition-all duration-300">
        {icon}
      </div>
      <p className="text-xs uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="text-lg font-bold text-foreground mt-0.5">{value}</p>
      <p className="text-[10px] text-muted-foreground">{detail}</p>
    </div>
  )
}