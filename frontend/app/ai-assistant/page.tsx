'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Trash2, Loader2, Sparkles, Bot, User, AlertCircle, StopCircle, MessageSquare, Database, BarChart3, TrendingUp, Search, Brain, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PageHeader } from '@/components/PageHeader'
import { queryBackend, clearBackendChat, parseBackendQueryResponse, type BackendQueryResult } from '@/lib/api'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  chartHtml?: string | null
  imageFile?: string | null
  imageFiles?: string[]
  htmlContent?: string | null
  timestamp: Date
}

const quickActions = [
  { icon: Search, label: 'EDA Summary', prompt: 'Run a comprehensive EDA on the active dataset including missing values, outliers, distributions, and key insights.' },
  { icon: BarChart3, label: 'Visualizations', prompt: 'What visualizations would you recommend for this dataset? Include chart types and what insights each would reveal.' },
  { icon: TrendingUp, label: 'Trend Analysis', prompt: 'Analyze trends over time in the dataset. Look at date-based patterns and seasonality.' },
  { icon: Database, label: 'Data Quality', prompt: 'Assess the data quality of the dataset. Highlight missing values, duplicates, data type issues, and anomalies.' },
  { icon: Brain, label: 'ML Recommendation', prompt: 'What machine learning models would be suitable for this dataset? Consider the data types and business context.' },
]

export default function AIAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `# 👋 Welcome to Insightly AI Assistant

I'm your data analytics copilot. I can help you with:

- **Exploratory Data Analysis** — missing values, distributions, outliers
- **Visualization Recommendations** — chart types and what they reveal
- **Statistical Analysis** — correlations, hypothesis tests, summaries
- **Machine Learning** — model recommendations and evaluation
- **Data Quality** — anomaly detection, duplicates, data profiling

Select a quick action below or type your question about the dataset.`,
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (content: string) => {
    if (!content.trim() || loading) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setError(null)
    setLoading(true)

    try {
      const payload = await queryBackend(content, 'ai-assistant')
      const parsed = parseBackendQueryResponse(payload)

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: parsed.text || 'The backend returned an empty response.',
        chartHtml: parsed.chartHtml,
        imageFile: parsed.imageFile,
        imageFiles: parsed.imageFiles,
        htmlContent: parsed.htmlContent,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to get response from backend'
      setError(errorMsg)

      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `❌ **Error**: ${errorMsg}\n\nPlease check that the backend is running and you are authenticated.`,
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleClear = async () => {
    setLoading(true)
    setError(null)
    try {
      await clearBackendChat()
      setMessages([
        {
          id: `clear-${Date.now()}`,
          role: 'assistant',
          content: 'Chat history has been cleared. How can I help you with your data?',
          timestamp: new Date(),
        },
      ])
    } catch {
      // Silently fail - local clear is fine
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage(input)
    }
  }

  return (
    <div className="h-full flex flex-col">
      <PageHeader
        badge="AI Analytics"
        title="AI Assistant"
        description="Your intelligent data analytics copilot. Ask questions, get insights, and explore your data."
      />

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mx-6 md:mx-8 mb-4 rounded-xl border border-destructive/20 bg-destructive/5 px-5 py-3 text-sm text-destructive flex items-start gap-3"
          >
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="font-medium">Backend Error</p>
              <p className="text-destructive/80 mt-0.5">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="p-1 hover:bg-white/10 rounded">
              <X size={14} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Area */}
      <div className="flex-1 mx-6 md:mx-8 mb-4 glass-card overflow-hidden flex flex-col">
        {/* Chat Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Bot size={18} className="text-primary" />
            <span className="text-sm font-semibold text-foreground">Analytics Chat</span>
            {loading && (
              <span className="text-xs text-muted-foreground animate-pulse">Thinking...</span>
            )}
          </div>
          <button
            onClick={() => void handleClear()}
            disabled={loading || messages.length <= 1}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors disabled:opacity-30"
            title="Clear chat"
          >
            <Trash2 size={15} className="text-muted-foreground" />
          </button>
        </div>

        {/* Messages */}
        <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 mt-1">
                  <Bot size={16} className="text-primary" />
                </div>
              )}

              <div className={`max-w-[75%] ${message.role === 'user' ? 'order-1' : ''}`}>
                <div
                  className={`px-4 py-3 rounded-2xl ${
                    message.role === 'user'
                      ? 'bg-primary/15 border border-primary/20 text-foreground'
                      : 'bg-white/5 border border-white/10 text-foreground'
                  }`}
                >
                  <div className="text-sm leading-relaxed space-y-2 prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        table: ({ node, ...props }) => (
                          <div className="my-3 overflow-x-auto rounded-xl border border-white/10 bg-black/20 shadow-lg">
                            <table className="w-full border-collapse text-xs text-left" {...props} />
                          </div>
                        ),
                        thead: ({ node, ...props }) => <thead className="border-b border-white/10 bg-white/5 font-semibold text-secondary/90" {...props} />,
                        tbody: ({ node, ...props }) => <tbody className="divide-y divide-white/5" {...props} />,
                        tr: ({ node, ...props }) => <tr className="hover:bg-white/5 transition-colors" {...props} />,
                        th: ({ node, ...props }) => <th className="px-3 py-2" {...props} />,
                        td: ({ node, ...props }) => <td className="px-3 py-2" {...props} />,
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                    {message.chartHtml && (
                      <div
                        className="mt-3 overflow-x-auto [&_img]:max-w-full [&_img]:h-auto [&_img]:rounded-lg [&_img]:border [&_img]:border-white/10"
                        dangerouslySetInnerHTML={{
                          __html: message.chartHtml.replace(/<image\b/gi, '<img'),
                        }}
                      />
                    )}
                    {((message.imageFiles && message.imageFiles.length > 0) || message.imageFile) && (
                      <div className="space-y-3 mt-3">
                        {(message.imageFiles && message.imageFiles.length > 0 ? message.imageFiles : [message.imageFile!]).map((imgBase64, index) => (
                          <div key={index} className="overflow-hidden rounded-xl border border-white/10 bg-black/45 hover:border-primary/30 transition-all duration-300 p-2 shadow-lg group">
                            <img
                              src={`data:image/png;base64,${imgBase64}`}
                              alt={`AI Generated Chart ${index + 1}`}
                              className="max-w-full h-auto rounded-lg transition-all duration-500 hover:scale-[1.02] cursor-zoom-in"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                    {message.htmlContent && (
                      <div className="mt-3 rounded-xl border border-white/10 bg-black/25 overflow-hidden shadow-lg">
                        <div className="border-b border-white/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-secondary/80 bg-white/5">
                          📋 Tabular Data
                        </div>
                        <div
                          className="p-3 overflow-x-auto text-[11px] [&_table]:w-full [&_table]:border-collapse [&_th]:border-b [&_th]:border-white/10 [&_th]:pb-1.5 [&_th]:text-left [&_th]:font-semibold [&_td]:py-1.5 [&_td]:border-b [&_td]:border-white/5 [&_tr:hover]:bg-white/5 transition-colors"
                          dangerouslySetInnerHTML={{ __html: message.htmlContent }}
                        />
                      </div>
                    )}
                  </div>
                </div>
                <p className="text-[10px] text-muted-foreground mt-1 px-1">
                  {message.role === 'user' ? 'You' : 'AI Assistant'} · {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center shrink-0 mt-1">
                  <User size={16} className="text-secondary" />
                </div>
              )}
            </motion.div>
          ))}

          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3"
            >
              <div className="w-8 h-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Bot size={16} className="text-primary" />
              </div>
              <div className="bg-white/5 border border-white/10 px-5 py-4 rounded-2xl">
                <div className="flex items-center gap-3">
                  <Loader2 size={16} className="animate-spin text-primary" />
                  <div className="flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-primary/40 typing-dot" />
                    <span className="w-2 h-2 rounded-full bg-primary/40 typing-dot" />
                    <span className="w-2 h-2 rounded-full bg-primary/40 typing-dot" />
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions (shown when chat is empty or at top) */}
        {messages.length <= 1 && !loading && (
          <div className="px-5 pb-4 border-t border-white/5 pt-4">
            <p className="text-xs text-muted-foreground mb-3 flex items-center gap-2">
              <Sparkles size={12} className="text-primary" />
              Quick Actions
            </p>
            <div className="flex flex-wrap gap-2">
              {quickActions.map((action) => {
                const Icon = action.icon
                return (
                  <button
                    key={action.label}
                    onClick={() => void sendMessage(action.prompt)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/5 transition-all"
                  >
                    <Icon size={12} className="text-primary" />
                    {action.label}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-white/10 p-4">
          <div className="flex items-center gap-3">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your data..."
              disabled={loading}
              className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all disabled:opacity-50 text-sm"
            />
            <button
              onClick={() => void sendMessage(input)}
              disabled={loading || !input.trim()}
              className="p-2.5 rounded-xl bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 hover:text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}