import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { generateAnswer } from '@/lib/llm'
import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://quick-caribou-824.convex.cloud')

const ChatRequestSchema = z.object({
  message: z.string().min(1),
  telegramUserId: z.string().optional(),
  instagramUserId: z.string().optional(),
  name: z.string().optional(),
})

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

    // 2. Get chat history for context
    // @ts-ignore
    const chatHistory = await convex.query('chat:getChatHistory', { userId: convexUserId, limit: 10 })
    const history = Array.isArray(chatHistory) ? chatHistory : []

    // 3. Search knowledge base
    // @ts-ignore
    const knowledgeItems = await convex.query('chat:searchKnowledgeBase', { query: message, limit: 5 })
    const knowledge = Array.isArray(knowledgeItems) ? knowledgeItems : []

    console.log('Knowledge items found:', knowledge.length, knowledge)

    // 4. Build context for LLM
    const context = buildContext(history, knowledge)

    // 5. Generate answer using LLM directly
    const answer = await generateAnswer(
      message,
      context,
      history.map((msg: { message: string }) => ({
        role: 'user' as const,
        content: msg.message,
      }))
    )

    // Extract sources from knowledge items
    const sources = knowledge.map((item: { url: string }) => item.url)
    console.log('Sources:', sources)

    // 6. Store the message and response
    // @ts-ignore
    await convex.mutation('chat:storeChatMessage', {
      userId: convexUserId,
      message,
      response: answer,
      sources,
    })

    // ManyChat expects this format
    return NextResponse.json({
      version: 'v2',
      content: {
        messages: [
          {
            type: 'text',
            text: answer,
          },
        ],
      },
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
