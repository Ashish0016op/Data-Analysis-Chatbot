'use client'

import { useState } from 'react'
import { Database, Upload, FileSpreadsheet, Search, Eye, Download, Loader2, AlertCircle, Filter, SortAsc, ChevronDown, ChevronRight } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { queryBackend, parseBackendQueryResponse } from '@/lib/api'

export default function Datasets() {
  const [queryInput, setQueryInput] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleQuery = async () => {
    if (!queryInput.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const payload = await queryBackend(queryInput, 'datasets')
      const parsed = parseBackendQueryResponse(payload)
      setResult(parsed.text)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl">
      <PageHeader
        badge="Data Assets"
        title="Datasets"
        description="Browse, preview, and manage your data assets. All operations are powered by the backend."
      />

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <ActionCard
          icon={<Search size={18} />}
          label="Browse Datasets"
          description="List all available datasets"
          onClick={() => setQueryInput('List all available datasets with their details')}
        />
        <ActionCard
          icon={<Eye size={18} />}
          label="Preview Data"
          description="Preview first rows of a dataset"
          onClick={() => setQueryInput('Show me the first 20 rows of the active dataset')}
        />
        <ActionCard
          icon={<Filter size={18} />}
          label="Schema Info"
          description="View column names and types"
          onClick={() => setQueryInput('Describe the schema of the active dataset including all column names, types, and constraints')}
        />
        <ActionCard
          icon={<Database size={18} />}
          label="Data Summary"
          description="Get dataset size and stats"
          onClick={() => setQueryInput('Summarize the active dataset: row count, column count, memory usage, and data types')}
        />
      </div>

      {/* Query Panel */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Database size={16} className="text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Query Datasets</h2>
        </div>
        <div className="flex gap-3">
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            placeholder="Ask about datasets, schema, previews..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 text-sm"
          />
          <button
            onClick={handleQuery}
            disabled={loading || !queryInput.trim()}
            className="px-5 py-2.5 rounded-xl bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 disabled:opacity-30 transition-all text-sm font-medium"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : 'Query'}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        {result && (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4">
            <pre className="text-sm text-foreground whitespace-pre-wrap font-sans leading-relaxed">{result}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

function ActionCard({ icon, label, description, onClick }: { icon: React.ReactNode; label: string; description: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="glass-card p-4 text-left group hover:border-primary/30 hover:bg-white/[0.02] transition-all">
      <div className="w-9 h-9 rounded-xl border border-white/10 bg-white/5 flex items-center justify-center text-muted-foreground mb-2 group-hover:bg-primary/10 group-hover:border-primary/30 group-hover:text-primary transition-all">
        {icon}
      </div>
      <p className="text-sm font-semibold text-foreground">{label}</p>
      <p className="text-xs text-muted-foreground mt-1">{description}</p>
    </button>
  )
}