'use client'

import { useState } from 'react'
import { Brain, TrendingUp, Activity, Network, Loader2, AlertCircle, Database, Sparkles, GitBranch, Eye } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { queryBackend } from '@/lib/api'
import { BackendResponse } from '@/components/BackendResponse'

const actions = [
  { icon: Brain, label: 'Model Recommendation', prompt: 'Analyze the dataset and recommend the best machine learning models. Consider data types, size, and business context.' },
  { icon: TrendingUp, label: 'Classification', prompt: 'Recommend and explain classification models suitable for this dataset. Include algorithm pros/cons and evaluation metrics.' },
  { icon: Activity, label: 'Regression', prompt: 'Analyze suitability for regression models. Recommend algorithms and explain feature-target relationships.' },
  { icon: Network, label: 'Clustering', prompt: 'Evaluate if clustering is appropriate for this dataset. Recommend algorithms and suggest optimal cluster counts.' },
  { icon: GitBranch, label: 'Feature Engineering', prompt: 'Suggest feature engineering techniques for this dataset: transformations, encodings, interactions, and feature selection methods.' },
  { icon: Database, label: 'Pipeline Design', prompt: 'Design a complete ML pipeline for this dataset: preprocessing, feature engineering, model selection, training, evaluation, and deployment considerations.' },
]

export default function MLStudio() {
  const [queryInput, setQueryInput] = useState('')
  const [result, setResult] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleQuery = async (prompt?: string) => {
    const q = prompt || queryInput
    if (!q.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const payload = await queryBackend(q, 'machine-learning')
      setResult(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ML query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl">
      <PageHeader
        badge="Machine Learning"
        title="ML Studio"
        description="End-to-end machine learning workflows. Model selection, training, evaluation, and deployment recommendations."
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
          <Brain size={16} className="text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Custom ML Request</h2>
        </div>
        <div className="flex gap-3">
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            placeholder="Ask about ML models, training, or evaluation..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 text-sm"
          />
          <button
            onClick={() => handleQuery()}
            disabled={loading || !queryInput.trim()}
            className="px-5 py-2.5 rounded-xl bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 disabled:opacity-30 transition-all text-sm font-medium"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : 'Analyze'}
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
            <div className="flex items-center gap-2 mb-3">
              <Brain size={14} className="text-primary" />
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">ML Analysis Results</span>
            </div>
            <BackendResponse payload={result} />
          </div>
        )}
      </div>
    </div>
  )
}