# Trigger.dev Reference - Knowledge Chatbot Project

## What is Trigger.dev?
- Open-source platform for building AI workflows in TypeScript
- Long-running tasks with retries, queues, observability, elastic scaling
- No timeouts (unlike AWS Lambda/Vercel)
- Built-in queuing, automatic retries, real-time monitoring

## Key Concepts

### Tasks
- Write tasks in your codebase using the `@trigger.dev/sdk`
- Long-running without timeouts
- Durable with checkpoints

### Triggering
- Can trigger tasks via API, scheduled (cron), or events
- REST API for external triggering

### Realtime API
- Subscribe to run updates in real-time
- Get status changes, metadata updates, stream data
- Works with React hooks or backend SDK

### Scheduled Tasks
- Cron-based scheduling
- Can schedule up to 1 year ahead
- Perfect for daily morning retrieval

## Project Plan: Knowledge Chatbot

### Architecture
```
[User] → [ManyChat] → [REST API (this project)] → [Trigger.dev] → [AI/LLM] → [Response]
                    ↑
            [Daily Scheduled Task]
                    ↓
            [Web Scraping/Search]
                    ↓
            [Knowledge Base Update]
```

### Components

1. **REST API** (Next.js)
   - Receives queries from ManyChat
   - Triggers Trigger.dev tasks
   - Returns responses

2. **Trigger.dev Tasks**
   - `answerQuery` - Takes user question, queries knowledge base, returns answer
   - `dailyRetrieval` - Scheduled daily to fetch data from websites
   - `updateKnowledgeBase` - Processes and stores scraped content

3. **Knowledge Base**
   - Stored in database (Postgres/Supabase)
   - Populated by daily retrieval
   - Queried when answering user questions

4. **ManyChat Integration**
   - Sends user messages to REST API
   - Receives and displays responses

### Tech Stack
- Next.js (API routes)
- Trigger.dev (workflow/orchestration)
- Supabase/Postgres (knowledge base storage)
- Brave Search MCP (web search)
- ManyChat (chatbot interface)

## Useful Links
- Docs: https://trigger.dev/docs
- API Reference: https://trigger.dev/docs/realtime
- GitHub: https://github.com/triggerdotdev/trigger.dev
