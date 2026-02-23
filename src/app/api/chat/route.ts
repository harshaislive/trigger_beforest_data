import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://quick-caribou-824.convex.cloud')

const MANYCHAT_API_KEY = process.env.MANYCHAT_API_KEY
const MANYCHAT_API_URL = 'https://api.manychat.com/fb/sending/sendContent'
const TRIGGERDEV_API_URL = process.env.TRIGGERDEV_API_URL
const TRIGGERDEV_API_KEY = process.env.TRIGGERDEV_API_KEY

const GREETINGS = ['hi', 'hello', 'hey', 'hiya', 'good morning', 'good evening', 'good afternoon', 'what\'s up', 'wassup', 'yo']

const ChatRequestSchema = z.object({
  message: z.string().min(1),
  telegramUserId: z.string().optional(),
  instagramUserId: z.string().optional(),
  name: z.string().optional(),
  contactId: z.string().optional(),
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

async function triggerDevTask(message: string, contactId: string, name?: string) {
  if (!TRIGGERDEV_API_URL || !TRIGGERDEV_API_KEY) {
    console.error('TRIGGERDEV_API_URL or TRIGGERDEV_API_KEY not configured')
    return
  }

  try {
    const response = await fetch(`${TRIGGERDEV_API_URL}/api/v1/tasks/answer-query/trigger`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${TRIGGERDEV_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        contactId,
        name,
      }),
    })

    const data = await response.json()
    console.log('Trigger.dev response:', data)
    return data
  } catch (error) {
    console.error('Error triggering Trigger.dev:', error)
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, telegramUserId, instagramUserId, name, contactId } = ChatRequestSchema.parse(body)

    const userId = telegramUserId || instagramUserId
    if (!userId && !contactId) {
      return NextResponse.json(
        { error: 'Either telegramUserId, instagramUserId, or contactId is required' },
        { status: 400 }
      )
    }

    // Check for greeting - handle immediately
    const isGreet = isGreeting(message)
    
    if (isGreet) {
      const answer = `[TriggerDev Bot] Hey there! 👋 I'm TriggerDev, your AI assistant. What would you like to know?`
      
      // Send greeting via ManyChat API (non-blocking)
      if (contactId && MANYCHAT_API_KEY) {
        sendManyChatMessage(contactId, answer).catch(console.error)
      }

      return NextResponse.json({
        version: 'v2',
        messages: [{ text: answer }],
        _timestamp: Date.now(),
      })
    }

    // For non-greetings, trigger Trigger.dev to handle async
    if (contactId && TRIGGERDEV_API_URL && TRIGGERDEV_API_KEY) {
      triggerDevTask(message, contactId, name).catch(console.error)
    }

    // Return immediate response to ManyChat
    return NextResponse.json({
      version: 'v2',
      messages: [{ text: 'I\'m processing your request...', _timestamp: Date.now() }],
    })
  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}
