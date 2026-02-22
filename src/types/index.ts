export interface KnowledgeItem {
  id: string
  url: string
  content: string
  summary?: string
  createdAt: string
  updatedAt: string
}

export interface ChatMessage {
  id: string
  userId: string
  message: string
  response?: string
  sources?: string[]
  createdAt: string
}

export interface WebSearchResult {
  title: string
  url: string
  description: string
}
