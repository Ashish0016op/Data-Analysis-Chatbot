'use client'

import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { parseBackendQueryResponse } from '@/lib/api'

import remarkGfm from 'remark-gfm'

interface BackendResponseProps {
  payload: unknown
  className?: string
}

function normalizeChartHtml(html: string) {
  return html.replace(/<image\b/gi, '<img')
}

export function BackendResponse({ payload, className = '' }: BackendResponseProps) {
  const { text, chartHtml, imageFile, imageFiles, htmlContent, hasChart } = useMemo(() => parseBackendQueryResponse(payload), [payload])
  const safeChartHtml = chartHtml ? normalizeChartHtml(chartHtml) : null

  return (
    <div className={`space-y-4 ${className}`}>
      {text && (
        <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ node, ...props }) => (
                <div className="my-4 overflow-x-auto rounded-xl border border-white/10 bg-black/20 shadow-lg">
                  <table className="w-full border-collapse text-xs text-left" {...props} />
                </div>
              ),
              thead: ({ node, ...props }) => <thead className="border-b border-white/10 bg-white/5 font-semibold text-secondary/90" {...props} />,
              tbody: ({ node, ...props }) => <tbody className="divide-y divide-white/5" {...props} />,
              tr: ({ node, ...props }) => <tr className="hover:bg-white/5 transition-colors" {...props} />,
              th: ({ node, ...props }) => <th className="px-4 py-2.5" {...props} />,
              td: ({ node, ...props }) => <td className="px-4 py-2.5" {...props} />,
            }}
          >
            {text}
          </ReactMarkdown>
        </div>
      )}

      {hasChart && imageFiles && imageFiles.length > 0 && (
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

      {hasChart && safeChartHtml && !imageFile && (
        <div className="rounded-lg border border-white/10 bg-black/20 overflow-hidden">
          <div className="border-b border-white/10 px-4 py-2 text-xs uppercase tracking-widest text-muted-foreground">
            Backend Chart
          </div>
          <div
            className="p-4 overflow-x-auto [&_img]:max-w-full [&_img]:h-auto [&_img]:rounded-md"
            dangerouslySetInnerHTML={{ __html: safeChartHtml }}
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

      {!text && !hasChart && !htmlContent && (
        <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground">
          {JSON.stringify(payload, null, 2)}
        </pre>
      )}
    </div>
  )
}
