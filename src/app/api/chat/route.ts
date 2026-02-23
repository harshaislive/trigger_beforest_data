import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { generateAnswer } from '@/lib/llm'
import { ConvexHttpClient } from 'convex/browser'

const CONVEX_URL = process.env.NEXT_PUBLIC_CONVEX_URL || 'https://quick-caribou-824.convex.cloud'
const convex = new ConvexHttpClient(CONVEX_URL)

const MANYCHAT_API_KEY = process.env.MANYCHAT_API_KEY
const MANYCHAT_API_URL = 'https://api.manychat.com/fb/sending/sendContent'
const BRAVE_API_KEY = process.env.BRAVE_API_KEY

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

async function searchBrave(query: string): Promise<string> {
  if (!BRAVE_API_KEY) {
    console.error('BRAVE_API_KEY not configured')
    return ''
  }

  try {
    const response = await fetch(`https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=5`, {
      headers: {
        'X-Subscription-Token': BRAVE_API_KEY,
      },
    })

    const data = await response.json()
    const results = data.web?.results || []
    
    return results.map((r: { title: string; description: string }) => 
      `${r.title}: ${r.description}`
    ).join('\n\n')
  } catch (error) {
    console.error('Brave search error:', error)
    return ''
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
    let convexUserId = ''
    
    if (isGreet) {
      answer = `Hey. I'm Forest Guide at Beforest. What would you like to know?`
    } else {
      // Get chat history for context
      let chatHistory: { role: string; content: string }[] = []
      
      const existingUserId = telegramUserId || instagramUserId || finalContactId
      
      if (existingUserId) {
        try {
          // @ts-ignore
          convexUserId = await convex.mutation('chat:getOrCreateUser', {
            telegramUserId: telegramUserId || undefined,
            instagramUserId: instagramUserId || undefined,
            contactId: finalContactId || undefined,
            name,
          })
          
          // @ts-ignore
          const history = await convex.query('chat:getChatHistory', { userId: convexUserId, limit: 6 })
          if (history && history.length > 0) {
            chatHistory = history.map((h: { message: string; response?: string }) => ({
              role: 'user',
              content: h.message,
            }))
            // Add assistant responses
            history.forEach((h: { message: string; response?: string }) => {
              if (h.response) {
                chatHistory.push({ role: 'assistant', content: h.response })
              }
            })
          }
        } catch (error) {
          console.error('History error:', error)
        }
      }

      // Search knowledge base
      let context = ''
      try {
        // @ts-ignore
        const knowledgeItems = await convex.query('chat:searchKnowledgeBase', { query: message, limit: 3 })
        console.log('Knowledge items found:', knowledgeItems?.length || 0)
        if (knowledgeItems && knowledgeItems.length > 0) {
          context = knowledgeItems.map((item: { content: string }) => item.content).join('\n\n')
          console.log('Context length:', context.length)
        }
      } catch (error) {
        console.error('Knowledge base error:', error)
      }

      // Fallback to Brave Search if no context
      if (!context && BRAVE_API_KEY) {
        console.log('Using Brave Search as fallback...')
        const braveResults = await searchBrave(`${message} Beforest`)
        if (braveResults) {
          context = `Web search results:\n${braveResults}`
        }
      }

      // Generate answer using LLM
      try {
        answer = await generateAnswer(message, context, chatHistory)
      } catch (error) {
        console.error('LLM error:', error)
        answer = "I'm not sure about that. What else would you like to know?"
      }
    }

    // Store message in Convex
    if (convexUserId) {
      try {
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
