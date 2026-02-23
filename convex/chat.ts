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

function cosineSimilarity(a: number[], b: number[]): number {
  if (!a.length || !b.length || a.length !== b.length) return 0
  let dot = 0
  let magA = 0
  let magB = 0
  for (let i = 0; i < a.length; i += 1) {
    const x = a[i]
    const y = b[i]
    dot += x * y
    magA += x * x
    magB += y * y
  }
  if (magA === 0 || magB === 0) return 0
  return dot / (Math.sqrt(magA) * Math.sqrt(magB))
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
    const now = Date.now()
    const id = await ctx.db.insert('chatMessages', {
      userId: args.userId,
      message: args.message,
      response: args.response,
      sources: args.sources,
      createdAt: now,
    })

    await ctx.db.patch(args.userId, {
      lastMessageAt: now,
      lastResponseAt: now,
      lastOutcome: 'responded',
    })

    return id
  },
})

export const updateLeadProfile = mutation({
  args: {
    userId: v.id('users'),
    leadIntent: v.optional(v.string()),
    leadScore: v.optional(v.number()),
    funnelStage: v.optional(v.string()),
    nextFollowUpAt: v.optional(v.number()),
    lastOutcome: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const patch: Record<string, string | number | undefined> = {}
    if (args.leadIntent !== undefined) patch.leadIntent = args.leadIntent
    if (args.leadScore !== undefined) patch.leadScore = args.leadScore
    if (args.funnelStage !== undefined) patch.funnelStage = args.funnelStage
    if (args.nextFollowUpAt !== undefined) patch.nextFollowUpAt = args.nextFollowUpAt
    if (args.lastOutcome !== undefined) patch.lastOutcome = args.lastOutcome

    await ctx.db.patch(args.userId, patch)
    return args.userId
  },
})

export const logLeadEvent = mutation({
  args: {
    userId: v.id('users'),
    eventType: v.string(),
    details: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert('leadEvents', {
      userId: args.userId,
      eventType: args.eventType,
      details: args.details,
      createdAt: Date.now(),
    })
  },
})

export const upsertPendingFollowUp = mutation({
  args: {
    userId: v.id('users'),
    scheduledFor: v.number(),
    messageDraft: v.string(),
    reason: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const pending = await ctx.db
      .query('followUps')
      .filter((q) => q.and(q.eq(q.field('userId'), args.userId), q.eq(q.field('status'), 'pending')))
      .first()

    if (pending) {
      await ctx.db.patch(pending._id, {
        scheduledFor: args.scheduledFor,
        messageDraft: args.messageDraft,
        reason: args.reason,
      })
      return pending._id
    }

    return await ctx.db.insert('followUps', {
      userId: args.userId,
      status: 'pending',
      scheduledFor: args.scheduledFor,
      messageDraft: args.messageDraft,
      reason: args.reason,
      createdAt: Date.now(),
    })
  },
})

export const getDueFollowUps = query({
  args: { now: v.optional(v.number()), limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const now = args.now ?? Date.now()
    const rows = await ctx.db
      .query('followUps')
      .withIndex('by_status_scheduled', (q) => q.eq('status', 'pending').lte('scheduledFor', now))
      .take(args.limit ?? 20)
    return rows
  },
})

export const markFollowUpSent = mutation({
  args: { followUpId: v.id('followUps') },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.followUpId, {
      status: 'sent',
      sentAt: Date.now(),
    })
    return args.followUpId
  },
})

export const registerIncomingMessage = mutation({
  args: {
    messageId: v.string(),
    contactId: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query('inboundMessages')
      .withIndex('by_message_id', (q) => q.eq('messageId', args.messageId))
      .first()

    if (existing) {
      return { isDuplicate: true, id: existing._id }
    }

    const id = await ctx.db.insert('inboundMessages', {
      messageId: args.messageId,
      contactId: args.contactId,
      createdAt: Date.now(),
    })

    return { isDuplicate: false, id }
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

export const upsertKnowledgeItem = mutation({
  args: {
    url: v.string(),
    title: v.optional(v.string()),
    content: v.string(),
    summary: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query('knowledgeItems')
      .filter((q) => q.eq(q.field('url'), args.url))
      .first()

    if (existing) {
      await ctx.db.patch(existing._id, {
        title: args.title,
        content: args.content,
        summary: args.summary,
        createdAt: Date.now(),
      })
      return existing._id
    }

    return await ctx.db.insert('knowledgeItems', {
      ...args,
      createdAt: Date.now(),
    })
  },
})

export const upsertCrawlUrl = mutation({
  args: {
    domain: v.string(),
    url: v.string(),
    pageType: v.optional(v.string()),
    source: v.optional(v.string()),
    lastmod: v.optional(v.string()),
    contentHash: v.optional(v.string()),
    title: v.optional(v.string()),
    status: v.string(),
    error: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const now = Date.now()
    const existing = await ctx.db
      .query('crawlUrls')
      .withIndex('by_url', (q) => q.eq('url', args.url))
      .first()

    if (existing) {
      await ctx.db.patch(existing._id, {
        domain: args.domain,
        pageType: args.pageType,
        source: args.source,
        lastmod: args.lastmod,
        contentHash: args.contentHash,
        title: args.title,
        status: args.status,
        error: args.error,
        lastCrawledAt: now,
        updatedAt: now,
      })
      return existing._id
    }

    return await ctx.db.insert('crawlUrls', {
      domain: args.domain,
      url: args.url,
      pageType: args.pageType,
      source: args.source,
      lastmod: args.lastmod,
      contentHash: args.contentHash,
      title: args.title,
      status: args.status,
      error: args.error,
      lastCrawledAt: now,
      createdAt: now,
      updatedAt: now,
    })
  },
})

export const upsertProduct = mutation({
  args: {
    brand: v.string(),
    domain: v.string(),
    name: v.string(),
    url: v.string(),
    category: v.optional(v.string()),
    availability: v.optional(v.string()),
    priceText: v.optional(v.string()),
    source: v.optional(v.string()),
    contentHash: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const now = Date.now()
    const existing = await ctx.db
      .query('products')
      .withIndex('by_url', (q) => q.eq('url', args.url))
      .first()

    if (existing) {
      await ctx.db.patch(existing._id, {
        brand: args.brand,
        domain: args.domain,
        name: args.name,
        category: args.category,
        availability: args.availability,
        priceText: args.priceText,
        source: args.source,
        contentHash: args.contentHash,
        updatedAt: now,
      })
      return existing._id
    }

    return await ctx.db.insert('products', {
      brand: args.brand,
      domain: args.domain,
      name: args.name,
      url: args.url,
      category: args.category,
      availability: args.availability,
      priceText: args.priceText,
      source: args.source,
      contentHash: args.contentHash,
      createdAt: now,
      updatedAt: now,
    })
  },
})

export const getProductsByBrand = query({
  args: { brand: v.string(), limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const rows = await ctx.db
      .query('products')
      .withIndex('by_brand', (q) => q.eq('brand', args.brand))
      .take(args.limit ?? 50)
    return rows
  },
})

export const getCrawlUrlByUrl = query({
  args: { url: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query('crawlUrls')
      .withIndex('by_url', (q) => q.eq('url', args.url))
      .first()
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

export const listKnowledgeItems = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    return await ctx.db.query('knowledgeItems').take(args.limit ?? 1000)
  },
})

export const upsertKnowledgeEmbedding = mutation({
  args: {
    knowledgeItemId: v.id('knowledgeItems'),
    embedding: v.array(v.number()),
    embeddingModel: v.string(),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.knowledgeItemId, {
      embedding: args.embedding,
      embeddingModel: args.embeddingModel,
      embeddingUpdatedAt: Date.now(),
    })
    return args.knowledgeItemId
  },
})

export const semanticSearchKnowledgeBase = query({
  args: { queryEmbedding: v.array(v.number()), limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const allItems = await ctx.db.query('knowledgeItems').take(1000)
    const scored = allItems
      .filter((item) => !!item.embedding && item.embedding.length === args.queryEmbedding.length)
      .map((item) => ({
        item,
        score: cosineSimilarity(item.embedding!, args.queryEmbedding),
      }))
      .filter((row) => row.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, args.limit ?? 5)
      .map((row) => row.item)
    return scored
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
