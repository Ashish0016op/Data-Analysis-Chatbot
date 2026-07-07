'use client'

import { useState } from 'react'
import { BarChart3, TrendingUp, PieChart, Activity, Loader2, AlertCircle, Database, LineChart, ScatterChart, Eye } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { queryBackend, parseBackendQueryResponse } from '@/lib/api'

const actions = [
  { icon: BarChart3, label: 'Bar Charts', prompt: 'What are the best bar chart visualizations for this dataset? Include the specific columns and what insights each would reveal.' },
  { icon: TrendingUp, label: 'Trend Lines', prompt: 'Create trend analysis visualizations for time-based columns in the dataset. Show patterns and seasonality.' },
  { icon: PieChart, label: 'Distribution', prompt: 'What pie/donut chart visualizations would you recommend for categorical columns? Show value distributions.' },
  { icon: Activity, label: 'Heatmaps', prompt: 'Create a correlation heatmap analysis for numeric columns. Highlight strong positive and negative correlations.' },
  { icon: ScatterChart, label: 'Scatter Plots', prompt: 'Recommend scatter plot visualizations for numeric column relationships. Include insights about correlations and clusters.' },
  { icon: Database, label: 'All Visuals', prompt: 'Generate a comprehensive visualization plan for this dataset covering all chart types and what each reveals about the data.' },
]

export default function Visualizations() {
  const [queryInput, setQueryInput] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const [chartHtml, setChartHtml] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<string | null>(null)
  const [imageFiles, setImageFiles] = useState<string[]>([])
  const [htmlContent, setHtmlContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleQuery = async (prompt?: string) => {
    const q = prompt || queryInput
    if (!q.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    setChartHtml(null)
    setImageFile(null)
    setImageFiles([])
    setHtmlContent(null)
    try {
      const payload = await queryBackend(q, 'visualizations')
      const parsed = parseBackendQueryResponse(payload)
      setResult(parsed.text)
      setChartHtml(parsed.chartHtml)
      setImageFile(parsed.imageFile)
      setImageFiles(parsed.imageFiles)
      setHtmlContent(parsed.htmlContent)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Visualization query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl">
      <PageHeader
        badge="Visual Analytics"
        title="Visualizations"
        description="Generate and explore data visualizations. Charts are created by the backend and displayed here."
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <button
              key={action.label}
              onClick={() => handleQuery(action.prompt)}
              disabled={loading}
              className="glass-card p-4 text-left group hover:border-primary/30 transition-all disabled:opacity-50"
            >
              <div className="w-9 h-9 rounded-xl border border-white/10 bg-white/5 flex items-center justify-center text-muted-foreground mb-2 group-hover:bg-primary/10 group-hover:border-primary/30 group-hover:text-primary transition-all">
                <Icon size={18} />
              </div>
              <p className="text-sm font-semibold text-foreground">{action.label}</p>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{action.prompt}</p>
            </button>
          )
        })}
      </div>

      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Eye size={16} className="text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Request Visualization</h2>
        </div>
        <div className="flex gap-3">
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            placeholder="Describe the visualization you want..."
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
          <div className="mt-6 space-y-6">
            <div className="rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-foreground whitespace-pre-wrap font-sans leading-relaxed">
              {result}
            </div>

            {imageFiles && imageFiles.length > 0 && (
              <div className="space-y-4">
                {imageFiles.map((imgBase64, index) => (
                  <div key={index} className="rounded-xl border border-white/10 bg-black/40 overflow-hidden shadow-2xl hover:border-primary/30 transition-all duration-300 group">
                    <div className="border-b border-white/10 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-primary/80 bg-white/5 flex items-center justify-between">
                      <span>📊 Visualization {imageFiles.length > 1 ? `#${index + 1}` : ''}</span>
                      <span className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity duration-300">Hover to expand</span>
                    </div>
                    <div className="p-4 flex justify-center bg-gradient-to-b from-white/[0.02] to-transparent overflow-hidden">
                      <img
                        src={`data:image/png;base64,${imgBase64}`}
                        alt={`Generated Data Visualization ${index + 1}`}
                        className="max-w-full h-auto rounded-lg shadow-md border border-white/10 transition-all duration-500 hover:scale-[1.03] cursor-zoom-in hover:shadow-primary/10 hover:shadow-2xl"
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {chartHtml && !imageFile && (
              <div className="rounded-xl border border-white/10 bg-black/20 overflow-hidden shadow-2xl">
                <div className="border-b border-white/10 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-primary/80 bg-white/5">
                  📊 Visualization (SVG)
                </div>
                <div
                  className="p-4 overflow-x-auto [&_img]:max-w-full [&_img]:h-auto [&_img]:rounded-lg [&_img]:border [&_img]:border-white/10"
                  dangerouslySetInnerHTML={{
                    __html: chartHtml.replace(/<image\b/gi, '<img'),
                  }}
                />
              </div>
            )}

            {htmlContent && (
              <div className="rounded-xl border border-white/10 bg-black/20 overflow-hidden shadow-2xl">
                <div className="border-b border-white/10 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-secondary/80 bg-white/5">
                  📋 Tabular Data
                </div>
                <div
                  className="p-4 overflow-x-auto text-xs [&_table]:w-full [&_table]:border-collapse [&_th]:border-b [&_th]:border-white/10 [&_th]:pb-2 [&_th]:text-left [&_th]:font-semibold [&_td]:py-2 [&_td]:border-b [&_td]:border-white/5 [&_tr:hover]:bg-white/5 transition-colors"
                  dangerouslySetInnerHTML={{ __html: htmlContent }}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}