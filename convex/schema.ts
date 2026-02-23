import { defineSchema, defineTable } from 'convex/server'
import { v } from 'convex/values'

export default defineSchema({
  users: defineTable({
    telegramUserId: v.optional(v.string()),
    instagramUserId: v.optional(v.string()),
    contactId: v.optional(v.string()),
    name: v.optional(v.string()),
    conversationState: v.optional(v.string()),
    lastMessageAt: v.optional(v.number()),
    createdAt: v.number(),
  }),

  chatMessages: defineTable({
    userId: v.id('users'),
    message: v.string(),
    response: v.optional(v.string()),
    sources: v.optional(v.array(v.string())),
    createdAt: v.number(),
  }).index('by_user', ['userId']),

  knowledgeItems: defineTable({
    url: v.string(),
    title: v.optional(v.string()),
    content: v.string(),
    summary: v.optional(v.string()),
    createdAt: v.number(),
  }),
})
