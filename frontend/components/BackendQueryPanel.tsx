'use client'

import { useState } from 'react'
import { Loader, Send } from 'lucide-react'
import { AnalyticsCard } from '@/components/CardComponents'
import { BackendResponse } from '@/components/BackendResponse'
import { ApiError, queryBackend } from '@/lib/api'

interface BackendQueryPanelProps {
  title: string
  subtitle?: string
  placeholder?: string
  defaultPrompt?: string
  context?: string
  examples?: string[]
}

export function BackendQueryPanel({
  title,
  subtitle,
  placeholder = 'Ask the backend for the analysis you need...',
  defaultPrompt = '',
  context,
  examples = [],
}: BackendQueryPanelProps) {
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [response, setResponse] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const runQuery = async (nextPrompt = prompt) => {
    const trimmed = nextPrompt.trim()
    if (!trimmed || loading) return

    setPrompt(trimmed)
    setLoading(true)
    setError(null)

    try {
      const payload = await queryBackend(trimmed, context)
      setResponse(payload)
    } catch (err) {
      setResponse(null)
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Backend query failed.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnalyticsCard title={title} subtitle={subtitle}>
      <div className="space-y-4">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void runQuery()
          }}
          className="space-y-3"
        >
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={placeholder}
            className="min-h-28 w-full resize-y rounded-lg bg-white/5 border border-white/10 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="submit"
              disabled={!prompt.trim() || loading}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? <Loader size={15} className="animate-spin" /> : <Send size={15} />}
              Send to Backend
            </button>
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => void runQuery(example)}
                className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-xs font-medium text-foreground hover:bg-white/10 hover:text-primary transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </form>

        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {response !== null && (
          <div className="rounded-lg border border-white/10 bg-black/20 overflow-hidden">
            <div className="border-b border-white/10 px-4 py-2 text-xs uppercase tracking-widest text-muted-foreground">
              Backend Response
            </div>
            <div className="max-h-[640px] overflow-auto p-4">
              <BackendResponse payload={response} />
            </div>
          </div>
        )}
      </div>
    </AnalyticsCard>
  )
}
