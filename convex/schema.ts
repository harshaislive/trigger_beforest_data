import { defineSchema, defineTable } from 'convex/server'
import { v } from 'convex/values'

export default defineSchema({
  users: defineTable({
    telegramUserId: v.optional(v.string()),
    instagramUserId: v.optional(v.string()),
    contactId: v.optional(v.string()),
    name: v.optional(v.string()),
    conversationState: v.optional(v.string()),
    leadIntent: v.optional(v.string()),
    leadScore: v.optional(v.number()),
    funnelStage: v.optional(v.string()),
    nextFollowUpAt: v.optional(v.number()),
    lastOutcome: v.optional(v.string()),
    lastMessageAt: v.optional(v.number()),
    lastResponseAt: v.optional(v.number()),
    createdAt: v.number(),
  }).index('by_contact_id', ['contactId']),

  chatMessages: defineTable({
    userId: v.id('users'),
    message: v.string(),
    response: v.optional(v.string()),
    sources: v.optional(v.array(v.string())),
    createdAt: v.number(),
  }).index('by_user', ['userId']),

  leadEvents: defineTable({
    userId: v.id('users'),
    eventType: v.string(),
    details: v.optional(v.string()),
    createdAt: v.number(),
  })
    .index('by_user', ['userId'])
    .index('by_type', ['eventType']),

  followUps: defineTable({
    userId: v.id('users'),
    status: v.string(),
    scheduledFor: v.number(),
    messageDraft: v.string(),
    reason: v.optional(v.string()),
    createdAt: v.number(),
    sentAt: v.optional(v.number()),
  })
    .index('by_user', ['userId'])
    .index('by_status_scheduled', ['status', 'scheduledFor']),

  inboundMessages: defineTable({
    messageId: v.string(),
    contactId: v.optional(v.string()),
    createdAt: v.number(),
  }).index('by_message_id', ['messageId']),

  crawlUrls: defineTable({
    domain: v.string(),
    url: v.string(),
    pageType: v.optional(v.string()),
    source: v.optional(v.string()),
    lastmod: v.optional(v.string()),
    contentHash: v.optional(v.string()),
    title: v.optional(v.string()),
    status: v.string(),
    lastCrawledAt: v.optional(v.number()),
    error: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
  })
    .index('by_url', ['url'])
    .index('by_domain', ['domain'])
    .index('by_status', ['status']),

  products: defineTable({
    brand: v.string(),
    domain: v.string(),
    name: v.string(),
    url: v.string(),
    category: v.optional(v.string()),
    availability: v.optional(v.string()),
    priceText: v.optional(v.string()),
    source: v.optional(v.string()),
    contentHash: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
  })
    .index('by_url', ['url'])
    .index('by_brand', ['brand'])
    .index('by_name', ['name']),

  knowledgeItems: defineTable({
    url: v.string(),
    title: v.optional(v.string()),
    content: v.string(),
    summary: v.optional(v.string()),
    embedding: v.optional(v.array(v.number())),
    embeddingModel: v.optional(v.string()),
    embeddingUpdatedAt: v.optional(v.number()),
    createdAt: v.number(),
  }),
})
