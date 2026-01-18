# Coup Game Frontend

A Next.js 14 frontend for the Coup card game, connecting to the Flask backend API.

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Framework | Next.js 14 + App Router | File-based routing, SSR |
| Language | TypeScript | Type safety |
| Styling | Tailwind CSS | Utility-first CSS |
| State | Zustand | Auth/user state management |
| Logging | loglevel | Environment-based log levels |
| Validation | Zod | Runtime schema validation |
| Data Fetching | React Query | Caching, mutations, infinite scroll |
| Animation | Framer Motion | Programmable animations |
| Animation | lottie-react | After Effects animations |
| Audio | use-sound | Sound effects and music |

## Pages

| Page | Route | Features |
|------|-------|----------|
| Start Page | `/` | Login form, OAuth buttons |
| Profile Page | `/profile/[playerId]` | Player info, platforms, session |
| Sessions Page | `/sessions` | Session list, join/create |

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Running Flask backend on port 4000

### Installation

```bash
cd game_server/frontend
npm install
```

### Environment Setup

Create environment files for each environment:

```bash
# .env.local (for local development)
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_ENVIRONMENT=local

# .env.development
NEXT_PUBLIC_API_URL=https://dev-api.example.com
NEXT_PUBLIC_ENVIRONMENT=development

# .env.qa
NEXT_PUBLIC_API_URL=https://qa-api.example.com
NEXT_PUBLIC_ENVIRONMENT=qa

# .env.production
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_ENVIRONMENT=production
```

### Running

```bash
# Local development (against localhost:4000)
npm run local

# Development server
npm run dev

# QA environment
npm run qa

# Production build
npm run prod
```

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx          # Root layout + providers
│   ├── page.tsx            # Start Page (login)
│   ├── profile/[playerId]/ # Profile Page
│   └── sessions/           # Sessions Page
├── components/
│   ├── ui/                 # Reusable UI components
│   ├── auth/               # Auth components (LoginForm, OAuth)
│   └── sessions/           # Session components
├── lib/
│   ├── api/                # API client and endpoints
│   ├── config.ts           # Runtime configuration
│   ├── constants.ts        # Static constants
│   └── logger.ts           # Logging utility
├── stores/
│   └── authStore.ts        # Zustand auth store
├── hooks/                  # Custom React hooks
├── types/                  # TypeScript types + Zod schemas
└── public/                 # Static assets
    ├── images/             # Card art, backgrounds
    ├── icons/              # Favicons, OAuth icons
    ├── audio/              # Sound effects, music
    └── animations/         # Lottie JSON files
```

## Environment Log Levels

| Environment | Log Level | What Shows |
|-------------|-----------|------------|
| local | debug | Everything |
| development | debug | Everything |
| qa | info | Info, warn, error |
| production | warn | Warn, error only |

## API Integration

The frontend connects to these Flask backend endpoints:

### Auth
- `POST /auth/login` - Username/password login
- `POST /auth/register` - Create account
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/oauth/{provider}` - OAuth redirect

### Sessions
- `GET /game/sessions` - List all sessions
- `GET /game/sessions/{id}` - Get session details
- `POST /game/sessions` - Create session
- `POST /game/sessions/{id}/join` - Join session

### Players
- `GET /players/{name}` - Get player profile

## Adding Assets

### Card Images
Add PNG files to `public/images/cards/`:
- duke.png, assassin.png, captain.png, ambassador.png, contessa.png, card-back.png

### OAuth Icons
Add SVG files to `public/icons/`:
- discord.svg, slack.svg, google.svg

### Sound Effects
Add MP3 files to `public/audio/sfx/`:
- coin.mp3, card-flip.mp3, challenge.mp3, success.mp3, fail.mp3

### Lottie Animations
Add JSON files from LottieFiles.com to `public/animations/`:
- coin-collect.json, card-reveal.json, victory.json, loading.json

## Development

### Type Safety

Types are defined with Zod schemas that provide both TypeScript types and runtime validation:

```typescript
import { PlayerSchema, Player } from '@/types';

// Type is inferred from schema
const player: Player = PlayerSchema.parse(apiResponse);
```

### State Management

Auth state is managed with Zustand and persisted to localStorage:

```typescript
import { useAuthStore } from '@/stores/authStore';

const { player, login, logout } = useAuthStore();
```

### API Calls

Use the typed API functions:

```typescript
import { loginUser, getSessions, getPlayer } from '@/lib/api';

const response = await loginUser({ username, password });
const sessions = await getSessions();
const player = await getPlayer('player_name');
```
