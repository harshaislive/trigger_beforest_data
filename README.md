# triggerdev-beforest

A knowledge-based chatbot built on Trigger.dev for ManyChat integration.

## Architecture

```
[User] → [ManyChat] → [REST API] → [Trigger.dev] → [AI/LLM] → [Response]
                    ↑
            [Daily Scheduled Task]
                    ↓
            [Web Scraping/Search]
                    ↓
            [Knowledge Base]
```

## Setup

### 1. Trigger.dev Setup

1. Create an account at [cloud.trigger.dev](https://cloud.trigger.dev)
2. Create a new project
3. Get your API key from project settings
4. Create tasks in the Trigger.dev dashboard:

#### Answer Query Task
```ts
// Task ID: answer-query
// Trigger via API
export const answerQuery = task({
  id: 'answer-query',
  retry: { maxAttempts: 3 },
  run: async (payload: { message: string; userId?: string; sessionId?: string }) => {
    // 1. Query knowledge base for relevant info
    // 2. Use LLM to generate answer
    // 3. Return { answer: string, sources: string[] }
    return { answer: 'Your answer here', sources: [] }
  },
})
```

#### Daily Retrieval Task (Scheduled)
```ts
// Task ID: daily-retrieval
// Schedule: 0 6 * * * (daily at 6 AM)
export const dailyRetrieval = task({
  id: 'daily-retrieval',
  schedule: { cron: '0 6 * * *', tz: 'UTC' },
  run: async () => {
    // 1. Use Brave Search to fetch data
    // 2. Store in knowledge base
    return { success: true }
  },
})
```

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `TRIGGER_API_KEY` - Your Trigger.dev API key
- `TRIGGER_API_URL` - Trigger.dev API URL (default: https://api.trigger.dev)
- `DATABASE_URL` - PostgreSQL connection string for knowledge base
- `BRAVE_API_KEY` - Your Brave Search API key

### 3. Run the App

```bash
npm run dev
```

The API will be available at:
- `GET /api/health` - Health check
- `POST /api/chat` - Send chat message

### 4. ManyChat Integration

Configure ManyChat to send POST requests to:
```
POST https://your-domain.com/api/chat
Body: { "message": "{{message}}" }
```

## API Endpoints

### POST /api/chat

Send a message to the chatbot.

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Trigger.dev?"}'
```

Response:
```json
{
  "answer": "Trigger.dev is...",
  "sources": ["https://trigger.dev"]
}
```

## Tech Stack

- Next.js 14 (App Router)
- Trigger.dev (workflow/orchestration)
- Brave Search MCP (web search)
- ManyChat (chatbot)
- PostgreSQL (knowledge base - to be added)
