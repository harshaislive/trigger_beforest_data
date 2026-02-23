const MINIMAX_API_URL = process.env.MINIMAX_API_URL || 'https://api.minimax.io/anthropic'
const MINIMAX_API_KEY = process.env.MINIMAX_API_KEY

export interface LLMMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface LLMResponse {
  content: string
  buttons?: { caption: string; payload: string }[]
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
      max_tokens: 512,
      messages: allMessages,
    }),
    signal: AbortSignal.timeout(25000), // 25 second timeout for LLM
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
): Promise<{ text: string; buttons?: { caption: string; payload: string }[] }> {
  const contextSection = context ? `Use information BELOW to answer. If nothing relevant, say you don't know:\n\n${context}\n\n` : ''
  
  const systemPrompt = `You are a team member at Beforest. You live and breathe this work.
  
About Beforest: We build regenerative communities where people live with the land, not off it. We have collectives in Coorg, Hyderabad, Mumbai, Bhopal.

How you respond:
- You ARE Beforest. Don't say "I work at" or "reach out to the team". Just answer.
- If info is provided, use it. If not, use what you genuinely know.
- If you truly don't know, say "I don't have that detail right now."
- Keep it brief. One or two sentences max.
- No emojis unless the conversation calls for it.
- Never sound like marketing. ${contextSection}

BUTTONS FORMAT (IMPORTANT):
When appropriate, you can suggest buttons for the user to click. Format buttons as:
[BUTTONS]
- caption: "Coffee Options", payload: "coffee_options"
- caption: "Rice Varieties", payload: "rice"
- caption: "Experiences", payload: "experiences"

Only include buttons when the user asks about:
- Products or pricing (coffee, rice, spices, etc.)
- Experiences or bookings
- More options or details
- Different categories to explore

The payload should be a simple lowercase_underscore identifier.
Do NOT include buttons for casual conversation or greetings.`




  const messages: LLMMessage[] = [
    ...chatHistory.map(msg => ({
      role: msg.role as 'user' | 'assistant',
      content: msg.content,
    })),
    { role: 'user', content: userMessage },
  ]

  const result = await callLLM(messages, systemPrompt)
  
  // Parse buttons from response
  const buttons: { caption: string; payload: string }[] = []
  if (result.content.includes('[BUTTONS]')) {
    const buttonSection = result.content.split('[BUTTONS]')[1]
    const buttonLines = buttonSection.split('\n').filter(line => line.includes('caption:'))
    for (const line of buttonLines) {
      const captionMatch = line.match(/caption:\s*"([^"]+)"/)
      const payloadMatch = line.match(/payload:\s*"([^"]+)"/)
      if (captionMatch && payloadMatch) {
        buttons.push({ caption: captionMatch[1], payload: payloadMatch[1] })
      }
    }
  }
  
  return {
    text: result.content.replace(/\[BUTTONS\][\s\S]*/g, '').trim(),
    buttons: buttons.length > 0 ? buttons : undefined
  }
}
