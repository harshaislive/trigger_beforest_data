import { query, mutation } from './_generated/server'
import { v } from 'convex/values'

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
    
    const queryLower = args.query.toLowerCase()
    const queryWords = queryLower.split(/\s+/).filter(w => w.length > 1)
    
    const scored = allItems.map(item => {
      const contentLower = item.content.toLowerCase()
      const titleLower = (item.title || '').toLowerCase()
      const urlLower = (item.url || '').toLowerCase()
      
      let score = 0
      
      for (const word of queryWords) {
        if (titleLower.includes(word)) score += 10
      }
      
      for (const word of queryWords) {
        if (urlLower.includes(word)) score += 5
      }
      
      for (const word of queryWords) {
        const matches = (contentLower.match(new RegExp(word, 'g')) || []).length
        score += matches
      }
      
      return { item, score }
    })
    
    return scored
      .filter(s => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, args.limit ?? 5)
      .map(s => s.item)
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
