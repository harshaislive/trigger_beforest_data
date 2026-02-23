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
  contactId: z.string().optional(),
  contact_id: z.string().optional(),
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
            type: 'instagram',
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
    const { message, telegramUserId, instagramUserId, name, contactId, contact_id } = ChatRequestSchema.parse(body)

    const userId = telegramUserId || instagramUserId
    if (!userId && !contactId && !contact_id) {
      return NextResponse.json(
        { error: 'Either telegramUserId, instagramUserId, or contactId is required' },
        { status: 400 }
      )
    }

    // Use contactId or contact_id (ManyChat sends snake_case)
    const finalContactId = contactId || contact_id

    // Check for greeting
    const isGreet = isGreeting(message)
    let answer: string
    
    if (isGreet) {
      answer = `Hey there! I'm TriggerDev. What would you like to know?`
    } else {
      // Generate answer using LLM
      try {
        answer = await generateAnswer(message, '', [])
      } catch (error) {
        console.error('LLM error:', error)
        answer = "I'm processing your request. Could you try again?"
      }
    }

    // Store message in Convex (blocking for now)
    const existingUserId = telegramUserId || instagramUserId || finalContactId
    if (existingUserId) {
      console.log('Storing to Convex:', { telegramUserId, instagramUserId, finalContactId, name })
      try {
        // @ts-ignore
        const convexUserId = await convex.mutation('chat:getOrCreateUser', {
          telegramUserId: telegramUserId || undefined,
          instagramUserId: instagramUserId || undefined,
          contactId: finalContactId || undefined,
          name,
        })
        console.log('Got convex user ID:', convexUserId)
        
        // @ts-ignore
        await convex.mutation('chat:storeChatMessage', {
          userId: convexUserId,
          message,
          response: answer,
          sources: [],
        })
        console.log('Stored chat message in Convex')
      } catch (error) {
        console.error('Convex error:', error)
      }
    }

    // Send via ManyChat API (non-blocking)
    if (finalContactId && MANYCHAT_API_KEY) {
      sendManyChatMessage(finalContactId, answer).catch(console.error)
    }

    // Return response to ManyChat
    return NextResponse.json({
      version: 'v2',
      messages: [{ text: answer }],
      _timestamp: Date.now(),
    })
  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}
