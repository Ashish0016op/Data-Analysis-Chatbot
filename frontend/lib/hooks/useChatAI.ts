import { useCallback, useState } from 'react'
import { clearBackendChat, parseBackendQueryResponse, queryBackend } from '@/lib/api'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  chartHtml?: string | null
  timestamp: Date
}

interface UseChatAIReturn {
  messages: ChatMessage[]
  loading: boolean
  error: Error | null
  sendMessage: (content: string) => Promise<void>
  clearHistory: () => Promise<void>
}

const initialMessage: ChatMessage = {
  id: '0',
  role: 'assistant',
  content: 'Connected to the backend analytics endpoint. Ask a question and I will send it to /query.',
  timestamp: new Date(),
}

export function useChatAI(): UseChatAIReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const sendMessage = useCallback(async (content: string) => {
    const trimmed = content.trim()
    if (!trimmed) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setLoading(true)
    setError(null)

    try {
      const payload = await queryBackend(trimmed, 'ai-assistant')
      const parsed = parseBackendQueryResponse(payload)
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: parsed.text,
        chartHtml: parsed.hasChart ? parsed.chartHtml : null,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to query backend')
      setError(error)
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          content: `Backend request failed: ${error.message}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }, [])

  const clearHistory = useCallback(async () => {
    setError(null)

    try {
      await clearBackendChat()
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to clear backend chat'))
    } finally {
      setMessages([{ ...initialMessage, timestamp: new Date() }])
    }
  }, [])

  return { messages, loading, error, sendMessage, clearHistory }
}
