import { query, mutation } from './_generated/server'
import { v } from 'convex/values'

export const getOrCreateUser = mutation({
  args: { telegramUserId: v.string(), name: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query('users')
      .filter((q) => q.eq(q.field('telegramUserId'), args.telegramUserId))
      .first()

    if (existing) {
      return existing._id
    }

    return await ctx.db.insert('users', {
      telegramUserId: args.telegramUserId,
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
    const allItems = await ctx.db.query('knowledgeItems').take(args.limit ?? 20)
    
    const queryLower = args.query.toLowerCase()
    return allItems.filter(item => 
      item.content.toLowerCase().includes(queryLower) ||
      (item.title && item.title.toLowerCase().includes(queryLower))
    )
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
