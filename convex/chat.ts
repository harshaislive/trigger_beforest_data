import { query, mutation } from './_generated/server'
import { v } from 'convex/values'

const STOP_WORDS = new Set([
  'a',
  'an',
  'and',
  'are',
  'as',
  'at',
  'be',
  'by',
  'for',
  'from',
  'how',
  'in',
  'is',
  'it',
  'of',
  'on',
  'or',
  'that',
  'the',
  'this',
  'to',
  'was',
  'what',
  'when',
  'where',
  'who',
  'why',
  'with',
])

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 1 && !STOP_WORDS.has(w))
}

function bm25Score(tf: number, df: number, docLength: number, avgDocLength: number, totalDocs: number): number {
  if (tf <= 0 || df <= 0 || docLength <= 0 || totalDocs <= 0) return 0

  const k1 = 1.2
  const b = 0.75
  const idf = Math.log(1 + (totalDocs - df + 0.5) / (df + 0.5))
  const norm = k1 * (1 - b + b * (docLength / Math.max(avgDocLength, 1)))
  return idf * ((tf * (k1 + 1)) / (tf + norm))
}

export const getOrCreateUser = mutation({
  args: { 
    telegramUserId: v.optional(v.string()), 
    instagramUserId: v.optional(v.string()),
    contactId: v.optional(v.string()),
    name: v.optional(v.string()) 
  },
  handler: async (ctx, args) => {
    const telegramId = args.telegramUserId
    const instagramId = args.instagramUserId
    const contactId = args.contactId

    if (telegramId) {
      const existing = await ctx.db
        .query('users')
        .filter((q) => q.eq(q.field('telegramUserId'), telegramId))
        .first()

      if (existing) {
        return existing._id
      }
    }

    if (instagramId) {
      const existing = await ctx.db
        .query('users')
        .filter((q) => q.eq(q.field('instagramUserId'), instagramId))
        .first()

      if (existing) {
        return existing._id
      }
    }

    if (contactId) {
      const existing = await ctx.db
        .query('users')
        .filter((q) => q.eq(q.field('contactId'), contactId))
        .first()

      if (existing) {
        return existing._id
      }
    }

    return await ctx.db.insert('users', {
      telegramUserId: args.telegramUserId,
      instagramUserId: args.instagramUserId,
      contactId: args.contactId,
      name: args.name,
      createdAt: Date.now(),
    })
  },
})

export const getChatHistory = query({
  args: { userId: v.id('users'), limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const messages = await ctx.db
      .query('chatMessages')
      .filter((q) => q.eq(q.field('userId'), args.userId))
      .order('desc')
      .take(args.limit ?? 50)

    return messages.reverse()
  },
})

export const storeChatMessage = mutation({
  args: {
    userId: v.id('users'),
    message: v.string(),
    response: v.optional(v.string()),
    sources: v.optional(v.array(v.string())),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert('chatMessages', {
      userId: args.userId,
      message: args.message,
      response: args.response,
      sources: args.sources,
      createdAt: Date.now(),
    })
  },
})

export const searchKnowledgeBase = query({
  args: { query: v.string(), limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const allItems = await ctx.db.query('knowledgeItems').take(100)

    if (!args.query) return allItems.slice(0, args.limit ?? 5)

    const queryTerms = tokenize(args.query)
    if (!queryTerms.length) return allItems.slice(0, args.limit ?? 5)

    const docs = allItems.map((item) => {
      const title = item.title || ''
      const url = item.url || ''
      const content = item.content || ''
      const combined = `${title} ${url} ${content}`
      const tokens = tokenize(combined)
      const tf = new Map<string, number>()

      for (const token of tokens) {
        tf.set(token, (tf.get(token) || 0) + 1)
      }

      return {
        item,
        titleLower: title.toLowerCase(),
        urlLower: url.toLowerCase(),
        contentLower: content.toLowerCase(),
        tf,
        docLength: tokens.length,
      }
    })

    const totalDocs = docs.length
    const avgDocLength =
      docs.reduce((sum, d) => sum + d.docLength, 0) / Math.max(totalDocs, 1)

    const docFreq = new Map<string, number>()
    for (const term of queryTerms) {
      let count = 0
      for (const doc of docs) {
        if ((doc.tf.get(term) || 0) > 0) count += 1
      }
      docFreq.set(term, count)
    }

    const scored = docs.map((doc) => {
      let score = 0

      for (const term of queryTerms) {
        score += bm25Score(
          doc.tf.get(term) || 0,
          docFreq.get(term) || 0,
          doc.docLength,
          avgDocLength,
          totalDocs,
        )
      }

      for (const term of queryTerms) {
        if (doc.titleLower.includes(term)) score += 2.5
        if (doc.urlLower.includes(term)) score += 1.25
      }

      if (doc.contentLower.includes(args.query.toLowerCase())) {
        score += 3
      }

      return { item: doc.item, score }
    })

    return scored
      .filter((s) => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, args.limit ?? 5)
      .map((s) => s.item)
  },
})

export const addKnowledgeItem = mutation({
  args: {
    url: v.string(),
    title: v.optional(v.string()),
    content: v.string(),
    summary: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert('knowledgeItems', {
      ...args,
      createdAt: Date.now(),
    })
  },
})

export const getRecentKnowledgeItems = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const items = await ctx.db
      .query('knowledgeItems')
      .order('desc')
      .take(args.limit ?? 10)
    return items.reverse()
  },
})

export const getUserByContactId = query({
  args: { contactId: v.string() },
  handler: async (ctx, args) => {
    const user = await ctx.db
      .query('users')
      .filter((q) => q.eq(q.field('contactId'), args.contactId))
      .first()
    return user
  },
})
