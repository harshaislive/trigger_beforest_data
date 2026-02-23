const MINIMAX_API_URL = process.env.MINIMAX_API_URL || 'https://api.minimax.io/anthropic'
const MINIMAX_API_KEY = process.env.MINIMAX_API_KEY

export interface LLMMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface LLMResponse {
  content: string
  usage?: {
    input_tokens: number
    output_tokens: number
  }
}

export async function callLLM(
  messages: LLMMessage[],
  systemPrompt?: string
): Promise<LLMResponse> {
  if (!MINIMAX_API_KEY) {
    throw new Error('MINIMAX_API_KEY not configured')
  }

  const allMessages = systemPrompt
    ? [{ role: 'system' as const, content: systemPrompt }, ...messages]
    : messages

  console.log('Calling Minimax API with:', { model: 'MiniMax-M2.5', messageCount: allMessages.length })

  const response = await fetch(`${MINIMAX_API_URL}/v1/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': MINIMAX_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'MiniMax-M2.5',
      max_tokens: 512, // Reduced for faster response
      messages: allMessages,
    }),
    signal: AbortSignal.timeout(8000), // 8 second timeout (leaves 2s buffer)
  })

  console.log('Minimax response status:', response.status)

  if (!response.ok) {
    const errorText = await response.text()
    console.error('Minimax error:', errorText)
    throw new Error(`Minimax API error: ${response.status} - ${errorText}`)
  }

  const data = await response.json()
  console.log('Minimax response data:', JSON.stringify(data).slice(0, 1000))
  
  // Handle different response structures
  let content = ''
  if (data.content) {
    if (Array.isArray(data.content)) {
      // Find the text type content
      const textItem = data.content.find((c: { type: string }) => c.type === 'text')
      content = textItem?.text || ''
    } else if (typeof data.content === 'string') {
      content = data.content
    }
  }
  
  return {
    content,
    usage: data.usage,
  }
}

export async function generateAnswer(
  userMessage: string,
  context: string,
  chatHistory: { role: string; content: string }[]
): Promise<string> {
  const contextSection = context ? `Context from knowledge base:\n${context}\n` : ''
  
  const systemPrompt = `You are TriggerDev - an AI assistant that helps users. ${contextSection}
IMPORTANT: Start EVERY response with this exact phrase: "[TriggerDev Bot] "
Instructions:
- Answer based on the context provided if available
- If no context is available, answer based on your general knowledge
- If you truly don't know something, say so honestly
- Be helpful, concise and direct`

  const messages: LLMMessage[] = [
    ...chatHistory.map(msg => ({
      role: msg.role as 'user' | 'assistant',
      content: msg.content,
    })),
    { role: 'user', content: userMessage },
  ]

  const result = await callLLM(messages, systemPrompt)
  return result.content
}
