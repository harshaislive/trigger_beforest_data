import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { generateAnswer } from '@/lib/llm'
import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://quick-caribou-824.convex.cloud')

const MANYCHAT_API_KEY = process.env.MANYCHAT_API_KEY
const MANYCHAT_API_URL = 'https://api.manychat.com/ig/sending/send'

const GREETINGS = ['hi', 'hello', 'hey', 'hiya', 'good morning', 'good evening', 'good afternoon', 'what\'s up', 'wassup', 'yo']

const ChatRequestSchema = z.object({
  message: z.string().min(1),
  telegramUserId: z.string().optional(),
  instagramUserId: z.string().optional(),
  name: z.string().optional(),
})

function isGreeting(message: string): boolean {
  const lower = message.toLowerCase().trim()
  return GREETINGS.some(g => lower === g || lower.startsWith(g + ' ') || lower.endsWith(' ' + g))
}

async function sendManyChatMessage(channelId: string, message: string) {
  if (!MANYCHAT_API_KEY) {
    console.error('MANYCHAT_API_KEY not configured')
    return
  }

  try {
    const response = await fetch(MANYCHAT_API_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${MANYCHAT_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        channel_id: channelId,
        message: message,
      }),
    })

    const data = await response.json()
    console.log('ManyChat response:', data)
    return data
  } catch (error) {
    console.error('Error sending ManyChat message:', error)
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, telegramUserId, instagramUserId, name } = ChatRequestSchema.parse(body)

    const userId = telegramUserId || instagramUserId
    if (!userId) {
      return NextResponse.json(
        { error: 'Either telegramUserId or instagramUserId is required' },
        { status: 400 }
      )
    }

    // 1. Get or create user in Convex
    // @ts-ignore
    const convexUserId = await convex.mutation('chat:getOrCreateUser', { 
      telegramUserId: telegramUserId || undefined, 
      instagramUserId: instagramUserId || undefined,
      name 
    })

    // 2. Get user conversation state
    // @ts-ignore
    const userState = await convex.query('chat:getUserState', { userId: convexUserId })
    const conversationState = userState?.conversationState || 'idle'

    console.log('User state:', conversationState, 'Message:', message)

    // 3. Smart greeting detection - if in idle and just greeting, ask for actual question
    if (conversationState === 'idle' && isGreeting(message)) {
      // @ts-ignore
      await convex.mutation('chat:updateUserState', { 
        userId: convexUserId, 
        conversationState: 'waiting_for_query' 
      })

      const greetingResponse = `[TriggerDev Bot] Hey there! 👋 I'm TriggerDev, your AI assistant. What would you like to know?`
      
      return NextResponse.json({
        version: 'v2',
        messages: [{ text: greetingResponse }],
      })
    }

    // 4. If waiting for query, process normally and reset state
    if (conversationState === 'waiting_for_query') {
      // @ts-ignore
      await convex.mutation('chat:updateUserState', { 
        userId: convexUserId, 
        conversationState: 'idle' 
      })
    }

    // 5. Get chat history for context
    // @ts-ignore
    const chatHistory = await convex.query('chat:getChatHistory', { userId: convexUserId, limit: 10 })
    const history = Array.isArray(chatHistory) ? chatHistory : []

    // 6. Search knowledge base
    // @ts-ignore
    const knowledgeItems = await convex.query('chat:searchKnowledgeBase', { query: message, limit: 5 })
    const knowledge = Array.isArray(knowledgeItems) ? knowledgeItems : []

    console.log('Knowledge items found:', knowledge.length)

    // 7. Build context for LLM
    const context = buildContext(history, knowledge)

    // 8. Generate answer using LLM
    const answer = await generateAnswer(
      message,
      context,
      history.map((msg: { message: string }) => ({
        role: 'user' as const,
        content: msg.message,
      }))
    )

    // 9. Extract sources
    const sources = knowledge.map((item: { url: string }) => item.url)
    console.log('Sources:', sources)

    // 10. Store the message and response
    // @ts-ignore
    await convex.mutation('chat:storeChatMessage', {
      userId: convexUserId,
      message,
      response: answer,
      sources,
    })

    // 11. Send via ManyChat API (for Instagram)
    if (instagramUserId && MANYCHAT_API_KEY) {
      await sendManyChatMessage(instagramUserId, answer)
    }

    // 12. Return response to ManyChat
    return NextResponse.json({
      version: 'v2',
      messages: [{ text: answer }],
    })
  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}

function buildContext(
  chatHistory: { message: string; response?: string }[],
  knowledgeItems: { content: string; url: string; title?: string }[]
): string {
  let context = ''

  if (knowledgeItems.length > 0) {
    context += 'Relevant knowledge:\n'
    knowledgeItems.forEach((item) => {
      context += `- ${item.title || item.url}: ${item.content.slice(0, 500)}\n`
    })
  }

  return context
}
