import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { generateAnswer } from '@/lib/llm'
import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://quick-caribou-824.convex.cloud')

const MANYCHAT_API_KEY = process.env.MANYCHAT_API_KEY
const MANYCHAT_API_URL = 'https://api.manychat.com/fb/sending/sendContent'

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

async function sendManyChatMessage(subscriberId: string, message: string) {
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
        subscriber_id: parseInt(subscriberId),
        data: {
          version: 'v2',
          content: {
            messages: [
              { type: 'text', text: message },
            ],
          },
        },
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

    // 2. Check for greeting - skip slow Convex query for now
    const isGreet = isGreeting(message)
    if (isGreet) {
      const greetingResponse = `[TriggerDev Bot] Hey there! 👋 I'm TriggerDev, your AI assistant. What would you like to know?`
      
      const greetingRes = NextResponse.json({
        version: 'v2',
        messages: [{ text: greetingResponse }],
        _timestamp: Date.now(),
      })
      greetingRes.headers.set('Cache-Control', 'no-store, must-revalidate')
      return greetingRes
    }

    // Skip Convex queries for now - just call LLM directly

    // 8. Generate answer using LLM (with timeout handling)
    let answer: string
    try {
      answer = await generateAnswer(message, '', [])
    } catch (error) {
      console.error('LLM error:', error)
      answer = "I'm processing your request. Could you try again?"
    }

    // Skip slow operations - store in background
    // @ts-ignore
    convex.mutation('chat:storeChatMessage', {
      userId: convexUserId,
      message,
      response: answer,
      sources: [],
    }).catch(console.error)

    // 11. Send via ManyChat API (for Instagram)
    if (instagramUserId && MANYCHAT_API_KEY) {
      await sendManyChatMessage(instagramUserId, answer)
    }

    // 12. Return response to ManyChat (add timestamp to prevent caching)
    const response = NextResponse.json({
      version: 'v2',
      messages: [{ text: answer }],
      _timestamp: Date.now(),
    })
    response.headers.set('Cache-Control', 'no-store, must-revalidate')
    return response
  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}
