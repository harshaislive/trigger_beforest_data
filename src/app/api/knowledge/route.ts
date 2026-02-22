import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://quick-caribou-824.convex.cloud')

const KnowledgeSchema = z.object({
  url: z.string(),
  title: z.string().optional(),
  content: z.string(),
  summary: z.string().optional(),
})

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const data = KnowledgeSchema.parse(body)

    // @ts-ignore - Convex client expects typed functions
    const id = await convex.mutation('chat:addKnowledgeItem', data)

    return NextResponse.json({ success: true, id })
  } catch (error) {
    console.error('Knowledge API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}
