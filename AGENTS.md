# AGENTS.md - Agentic Coding Guidelines

## Project Overview

This directory contains the triggerdev_beforest project - a knowledge-based chatbot built on Trigger.dev.

### Architecture
```
[User] → [ManyChat] → [REST API] → [Trigger.dev] → [AI/LLM] → [Response]
                    ↑
            [Daily Scheduled Task]
                    ↓
            [Web Scraping/Search]
                    ↓
            [Knowledge Base Update]
```

### Tech Stack
- Next.js (REST API)
- Trigger.dev (workflow orchestration)
- Supabase/Postgres (knowledge base)
- Brave Search MCP (web search)
- ManyChat (chatbot interface)

### Key Features
- Daily morning retrieval to fetch data from websites
- Knowledge base populated by scheduled tasks
- REST API for ManyChat integration
- Real-time responses via Trigger.dev Realtime API

---

## Build, Lint, and Test Commands

### Package Manager
This project uses [pnpm/npm/yarn]. Update based on actual usage.

### Core Commands

```bash
pnpm install    # Install dependencies
pnpm dev        # Run development server
pnpm build      # Build for production
pnpm start      # Start production server
pnpm lint       # Run linter
pnpm typecheck  # Run type checker
pnpm check      # Run all checks (lint + typecheck + test)
```

### Running Tests

```bash
pnpm test              # Run all tests
pnpm test:watch        # Run tests in watch mode
pnpm test:coverage     # Run tests with coverage
pnpm test path/to/file.test.ts  # Run single test file
pnpm test -t "pattern" # Run tests matching pattern
pnpm test:ci           # Run tests in CI mode (once)
```

---

## Code Style Guidelines

### General Principles
- Keep functions small and focused (single responsibility)
- Write self-documenting code with clear variable/function names
- Prefer explicit over implicit; avoid magic numbers - use constants
- Handle errors explicitly, never silently

### TypeScript/Type Safety
- Always use TypeScript - no plain JavaScript files
- Enable strict mode in tsconfig.json
- Define explicit return types for functions
- Use interfaces over types for object shapes
- Avoid `any` - use `unknown` when type is uncertain
- Use generics for reusable components
- Validate external data with zod/schemas at API boundaries

### Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Files (components) | PascalCase | `UserProfile.tsx` |
| Files (utilities) | camelCase | `useAuth.ts` |
| Functions/Variables | camelCase | `getUserById()` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Components | PascalCase | `UserProfile` |
| Boolean variables | is/has/can prefixes | `isActive` |

### Imports (order: external → internal → relative)
```typescript
import { useState } from 'react'
import { trpc } from '@/lib/trpc'
import { Button } from '@/components/ui/button'
import { UserCard } from './UserCard'
// Use @/ path aliases; avoid relative imports beyond 2 levels
```

### Formatting
- Use Prettier (2 spaces indentation)
- Max line length: 100 characters
- Use semicolons and trailing commas
- Single quotes for strings; template literals for interpolation

### React/Next.js Guidelines
```typescript
export function UserProfile({ userId }: UserProfileProps) {
  const { data: user, isLoading } = useUser(userId)
  if (isLoading) return <Skeleton />
  return <div><h1>{user.name}</h1></div>
}

interface UserProfileProps { userId: string }
```
- Use functional components only
- Use `function` declarations for exported components
- Colocate component props interfaces with components
- Extract custom hooks for reusable logic; use early returns

### Error Handling
- Always use try-catch for async operations
- Log errors with context for debugging
- Throw specific error types for expected failures
- Never swallow errors silently
- Consider Result types for operations that can fail predictably

### Database/ORM
- Use Prisma/Drizzle for database access
- Always use parameterized queries - never string concatenation
- Use transactions for multi-step operations
- Add indexes for frequently queried fields

### Testing Guidelines
```typescript
describe('formatCurrency', () => {
  it('formats USD correctly', () => {
    expect(formatCurrency(100, 'USD')).toBe('$100.00')
  })
  it('throws for invalid currency', () => {
    expect(() => formatCurrency(100, 'INVALID')).toThrow()
  })
})
```
- Name test files: `*.test.ts` or `*.spec.ts`
- Use meaningful test names: `it('should return user when valid id provided')`
- Follow AAA pattern: Arrange, Act, Assert
- Mock external dependencies (API, database)

### Git Conventions
- Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
- Keep commits atomic and focused

---

## Project Structure
```
src/
├── app/                    # Next.js App Router pages
│   ├── api/
│   │   ├── chat/          # POST /api/chat - ManyChat integration
│   │   └── health/        # Health check endpoint
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── lib/
│   └── trigger-client.ts   # Trigger.dev API client
└── types/
    └── index.ts            # Shared TypeScript types
```

### Trigger.dev Tasks
Tasks are defined in the Trigger.dev dashboard, not in this repo. This project triggers tasks via the Trigger.dev REST API.

- `answer-query` - Answer user questions
- `daily-retrieval` - Scheduled daily web scraping (6 AM UTC)

---

## Environment Variables
Required (add to `.env`): `DATABASE_URL`, `AUTH_SECRET`, `API_URL`
Never commit `.env` files. Use `.env.example` for templates.

---

## Dependencies (Do Not Install)
Without explicit approval, do NOT install new UI libraries, database clients beyond configured ORM, authentication libraries beyond current setup, or heavy runtime dependencies.

This project uses the Trigger.dev REST API directly (not the SDK) - tasks are defined in the Trigger.dev dashboard.

## Available MCP Tools

### Brave Search
This project has Brave Search MCP configured:
- `brave_web_search` - Web search with results
- `brave_image_search` - Image search
- `brave_news_search` - News search
- `brave_video_search` - Video search

---

## When in Doubt
- Follow existing code patterns in the codebase
- Ask for clarification if requirements are unclear
- Run lint/typecheck before committing
- Write tests for new functionality
