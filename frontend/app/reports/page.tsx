'use client'

import { useState } from 'react'
import { FileText, Download, Loader2, AlertCircle, Database, Sparkles, Eye, Printer, Share2 } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { queryBackend, parseBackendQueryResponse } from '@/lib/api'

const actions = [
  { icon: FileText, label: 'Full Report', prompt: 'Generate a comprehensive data analysis report covering: dataset overview, data quality, EDA findings, statistical insights, visualization recommendations, and ML opportunities.' },
  { icon: Database, label: 'Data Summary', prompt: 'Create a concise data summary report: row count, column types, missing values, memory usage, and key statistics for all columns.' },
  { icon: Sparkles, label: 'Executive Summary', prompt: 'Write an executive summary of the dataset: key metrics, major findings, potential issues, and actionable recommendations for stakeholders.' },
  { icon: Eye, label: 'Quality Report', prompt: 'Generate a data quality assessment report: completeness, uniqueness, consistency, accuracy issues, and recommended remediation steps.' },
]

export default function Reports() {
  const [queryInput, setQueryInput] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleQuery = async (prompt?: string) => {
    const q = prompt || queryInput
    if (!q.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const payload = await queryBackend(q, 'reports')
      const parsed = parseBackendQueryResponse(payload)
      setResult(parsed.text)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Report generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl">
      <PageHeader
        badge="Reports & Documentation"
        title="Reports"
        description="Generate comprehensive data analysis reports. Export insights for stakeholders."
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <button
              key={action.label}
              onClick={() => handleQuery(action.prompt)}
              disabled={loading}
              className="glass-card p-5 text-left group hover:border-primary/30 transition-all disabled:opacity-50"
            >
              <div className="w-10 h-10 rounded-xl border border-white/10 bg-white/5 flex items-center justify-center text-muted-foreground mb-3 group-hover:bg-primary/10 group-hover:border-primary/30 group-hover:text-primary transition-all">
                <Icon size={20} />
              </div>
              <p className="text-sm font-semibold text-foreground">{action.label}</p>
              <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">{action.prompt}</p>
            </button>
          )
        })}
      </div>

      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <FileText size={16} className="text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Custom Report Request</h2>
        </div>
        <div className="flex gap-3">
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            placeholder="Describe the report you need..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 text-sm"
          />
          <button
            onClick={() => handleQuery()}
            disabled={loading || !queryInput.trim()}
            className="px-5 py-2.5 rounded-xl bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 disabled:opacity-30 transition-all text-sm font-medium"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : 'Generate'}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        {result && (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-primary" />
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Generated Report</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => navigator.clipboard.writeText(result)}
                  className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-muted-foreground hover:text-foreground transition-colors"
                  title="Copy to clipboard"
                >
                  <Printer size={14} />
                </button>
              </div>
            </div>
            <pre className="text-sm text-foreground whitespace-pre-wrap font-sans leading-relaxed">{result}</pre>
          </div>
        )}
      </div>
    </div>
  )
}