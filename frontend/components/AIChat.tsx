'use client'

import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Send, Trash2, Loader } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  chartHtml?: string | null
  timestamp: Date
}

interface AIChatProps {
  messages: ChatMessage[]
  onSendMessage: (content: string) => Promise<void>
  onClearHistory: () => void | Promise<void>
  loading?: boolean
}

export function AIChat({ messages, onSendMessage, onClearHistory, loading = false }: AIChatProps) {
  const [input, setInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim() || isSubmitting || loading) return

    setIsSubmitting(true)
    try {
      await onSendMessage(input)
      setInput('')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClearHistory = async () => {
    if (isClearing) return

    setIsClearing(true)
    try {
      await onClearHistory()
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-background to-background/80">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-foreground">AI Analytics Assistant</h2>
        <button
          onClick={() => void handleClearHistory()}
          disabled={isClearing}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
          title="Clear chat history"
        >
          {isClearing ? (
            <Loader size={18} className="text-muted-foreground animate-spin" />
          ) : (
            <Trash2 size={18} className="text-muted-foreground" />
          )}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message, index) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-2xl px-4 py-3 rounded-xl ${
                message.role === 'user'
                  ? 'bg-primary/20 border border-primary/30 text-foreground'
                  : 'bg-white/5 border border-white/10 text-foreground'
              }`}
            >
              <div className="text-sm leading-relaxed space-y-2 prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{message.content}</ReactMarkdown>
                {message.chartHtml && (
                  <div
                    className="mt-3 overflow-x-auto [&_img]:max-w-full [&_img]:h-auto [&_img]:rounded-md"
                    dangerouslySetInnerHTML={{
                      __html: message.chartHtml.replace(/<image\b/gi, '<img'),
                    }}
                  />
                )}
              </div>
              <span className="text-xs text-muted-foreground mt-2 block">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </motion.div>
        ))}

        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="bg-white/5 border border-white/10 px-4 py-3 rounded-xl flex items-center space-x-2">
              <Loader size={16} className="text-primary animate-spin" />
              <span className="text-sm text-muted-foreground">AI is thinking...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center space-x-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
            placeholder="Ask about your data..."
            disabled={isSubmitting || loading}
            className="flex-1 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary transition-colors disabled:opacity-50"
          />
          <button
            onClick={handleSendMessage}
            disabled={isSubmitting || loading || !input.trim()}
            className="p-2 rounded-lg bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
