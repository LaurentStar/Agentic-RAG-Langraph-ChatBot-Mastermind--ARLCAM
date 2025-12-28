<p align="center">
  <img src="readme_presentation/slack_title.png" alt="Slack Bot" width="600">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/slack_bolt-1.18+-4A154B?logo=slack&logoColor=white">
  <img src="https://img.shields.io/badge/flask-3.0+-green?logo=flask&logoColor=white">
  <img src="https://img.shields.io/badge/postgresql-15+-blue?logo=postgresql&logoColor=white">
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,flask,postgres" />
</p>

<p align="center">
  <strong>Slack bot for the Coup card game with slash commands and game server integration.</strong>
</p>

---

> **Quick Start**
> ```bash
> cd slack_bot
> pip install -r requirements.txt
> python bot.py
> # Bot listens for Slack events and Flask API runs on http://localhost:3002
> ```

---

## 📑 Table of Contents

- [📖 Overview](#-overview)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [⚡ Slash Commands](#-slash-commands)
- [🔌 API Endpoints](#-api-endpoints)
- [👂 Listeners](#-listeners)
- [🛠️ Services](#️-services)
- [🚀 Setup](#-setup)
- [⚙️ Environment Variables](#️-environment-variables)
- [👨‍💻 Author](#-author)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

---

## 📖 Overview

The **Slack Bot** serves as the Slack interface for the Coup card game. It connects Slack users to the game server, enabling them to:

- Join and manage game sessions via slash commands
- Chat in-game with messages forwarded to the game server
- Receive broadcasts from other platforms (Discord, etc.)
- Authenticate via Slack OAuth for seamless account linking

**Key Capabilities:**
- Event-driven architecture via Slack Bolt
- Flask-RESTX API for receiving broadcasts and admin operations
- PostgreSQL logging and token caching
- Parity with Discord bot features

---

## ✨ Features

### Bot Framework

| Feature | Status | Description |
|---------|--------|-------------|
| Slack Bolt | ✅ | Event-driven bot framework |
| Slash Commands | ✅ | Native Slack slash commands |
| Event Listeners | ✅ | Message and interaction handlers |
| Flask Integration | ✅ | Bolt adapter for Flask routes |

### Authentication

| Feature | Status | Description |
|---------|--------|-------------|
| OAuth Integration | ✅ | Slack OAuth via game server |
| Token Caching | ✅ | PostgreSQL-backed JWT cache per user |
| `@requires_linked_account` | ✅ | Decorator for auth-required commands |
| Admin Privilege Checks | ✅ | `@admin_only` decorator |

### Database & Infrastructure

| Feature | Status | Description |
|---------|--------|-------------|
| Auto-Create Tables | ✅ | SQLAlchemy creates tables on startup |
| PostgreSQL Logging | ✅ | Persistent command/message logging |
| Health/Readiness Checks | ✅ | `/health` and `/health/ready` endpoints |
| Graceful Shutdown | ✅ | Clean disconnect on SIGINT/SIGTERM |

### Flask-RESTX APIs

| Feature | Status | Description |
|---------|--------|-------------|
| Broadcast Endpoint | ✅ | Receive messages from game server |
| Admin Endpoints | ✅ | Bot info, token cache management |
| Swagger UI | ✅ | Interactive API docs at `/docs` |

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Slack
        User[Slack User]
        Channel[Slack Channel]
    end
    
    subgraph SlackBot[Slack Bot]
        Bolt[Slack Bolt App]
        Listeners[Event Listeners]
        Flask[Flask-RESTX API]
        DB[(PostgreSQL)]
    end
    
    subgraph External
        GameServer[Game Server]
    end
    
    User -->|Slash Command| Bolt
    Bolt --> Listeners
    Listeners -->|API Call| GameServer
    GameServer -->|Broadcast| Flask
    Flask -->|Post Message| Channel
    Bolt --> DB
    Flask --> DB
```

### Folder Structure

```
slack_bot/
├── app/
│   ├── __init__.py              # Application factory
│   ├── constants.py             # Enums and constants
│   ├── extensions.py            # Flask extensions
│   ├── apis/                    # Flask-RESTX namespaces
│   │   ├── admin_ns.py          # Admin operations
│   │   ├── broadcast_ns.py      # Message broadcasting
│   │   └── health_ns.py         # Health checks
│   ├── bots/
│   │   └── slack_bot.py         # Slack Bolt wrapper
│   ├── config/
│   │   └── logging_config.py    # Logging setup
│   ├── database/
│   │   └── db_models.py         # ORM models
│   ├── decorators/
│   │   └── auth.py              # Auth decorators
│   ├── lifecycle/               # Startup/shutdown
│   ├── listeners/               # Slack event handlers
│   │   ├── admin_commands.py    # Game session commands
│   │   └── game_chat.py         # Chat forwarding
│   ├── models/                  # API models
│   └── services/                # Business logic
├── bot.py                       # Entry point
├── requirements.txt             # Production dependencies
└── requirements-local.txt       # Local dev dependencies
```

---

## ⚡ Slash Commands

### Game Session Commands

| Command | Description | Auth Required |
|---------|-------------|---------------|
| `/game_session-list` | List available game sessions | ✅ |
| `/game_session-create` | Create a new game session | ✅ Admin |
| `/game_session-register-channel` | Register channel for broadcasts | ✅ Admin |

---

## 🔌 API Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/health` | GET | Health check |
| `/health/ready` | GET | Readiness check |
| `/broadcast` | POST | Receive message from game server |
| `/admin/bot-info` | GET | Get bot information |
| `/admin/token-cache` | GET | Get token cache stats |
| `/admin/token-cache` | DELETE | Clean expired tokens |

### Slack Event Routes

| Path | Method | Description |
|------|--------|-------------|
| `/slack/events` | POST | Slack event subscription |
| `/slack/commands` | POST | Slash command handler |
| `/slack/interactions` | POST | Interactive component handler |
| `/slack/options` | POST | Dynamic select menu options |

### Sample API Requests

<details>
<summary><strong>Broadcast: Send Message to Channel</strong></summary>

```bash
curl -X POST http://localhost:3002/broadcast \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "C1234567890",
    "message": "Game starting in 5 minutes!",
    "session_id": "sess_abc123"
  }'
```
</details>

<details>
<summary><strong>Admin: Get Bot Info</strong></summary>

```bash
curl -X GET http://localhost:3002/admin/bot-info \
  -H "Authorization: Bearer <jwt_token>"
```

**Response:**
```json
{
  "connected": true,
  "bot_id": "U1234567890",
  "bot_name": "CoupBot"
}
```
</details>

<details>
<summary><strong>Health Check</strong></summary>

```bash
curl -X GET http://localhost:3002/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-28T12:00:00Z"
}
```
</details>

---

## 👂 Listeners

| Listener | File | Description |
|----------|------|-------------|
| `admin_commands` | `admin_commands.py` | Game session slash commands |
| `game_chat` | `game_chat.py` | Forward messages to game server |

---

## 🛠️ Services

| Service | Responsibility |
|---------|----------------|
| `AuthService` | JWT token validation |
| `BroadcastService` | Post messages to Slack channels |
| `HealthService` | Health and readiness checks |
| `LoggingService` | Database logging |
| `TokenCacheService` | PostgreSQL token cache |

---

## 🚀 Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Slack App (from [Slack API](https://api.slack.com/apps))

### Installation

```bash
# Navigate to slack_bot directory
cd slack_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# For local development (includes testing tools)
pip install -r requirements-local.txt
```

### Slack App Setup

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app "From scratch"
3. Configure OAuth & Permissions:
   - Bot Token Scopes: `chat:write`, `commands`, `users:read`
   - User Token Scopes: `identity.basic`, `identity.email`
4. Configure Slash Commands:
   - `/game_session-list` → `https://your-domain/slack/commands`
   - `/game_session-create` → `https://your-domain/slack/commands`
5. Configure Event Subscriptions:
   - Request URL: `https://your-domain/slack/events`
   - Subscribe to: `message.channels`, `app_mention`
6. Configure Interactivity:
   - Request URL: `https://your-domain/slack/interactions`
7. Install app to workspace
8. Copy Bot Token and Signing Secret

### Running the Bot

```bash
# Set environment variables (or use .env file)
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_SIGNING_SECRET=your-secret

# Run the bot
python bot.py
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | Yes | - | Slack bot token (xoxb-...) |
| `SLACK_SIGNING_SECRET` | Yes | - | Slack signing secret |
| `SLACK_BOT_DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `SLACK_BOT_PORT` | No | `3002` | Flask API port |
| `GAME_SERVER_URL` | Yes | - | Game server URL |
| `JWT_SECRET_KEY` | Yes | - | Secret for JWT validation |
| `SLACK_GAME_CHANNEL` | No | - | Default game channel ID |
| `ENVIRONMENT` | No | `local` | Environment (local/dev/qa/prod) |

---

## 👨‍💻 Author

**Laurent Mundell** - *By Any Means Developer*

<p>
  <a href="https://github.com/LaurentStar"><img src="https://img.shields.io/badge/GitHub-LaurentStar-181717?logo=github"></a>
  <a href="https://medium.com/@laurent.mundell"><img src="https://img.shields.io/badge/Medium-@laurent.mundell-000000?logo=medium"></a>
  <a href="https://www.hackerrank.com/profile/laurent_mundell"><img src="https://img.shields.io/badge/HackerRank-laurent__mundell-00EA64?logo=hackerrank&logoColor=white"></a>
  <a href="http://www.linkedin.com/in/christian-mundell-90733555"><img src="https://img.shields.io/badge/LinkedIn-Christian%20Mundell-0A66C2?logo=linkedin"></a>
</p>

> "I never surrender, even to impossible problems! I always find a way forward no matter how difficult the hunt."

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE.md) file for details.

<p>
  <img src="https://img.shields.io/badge/license-MIT-green?logo=opensourceinitiative&logoColor=white">
</p>

---

## 🙏 Acknowledgments

- [Slack Bolt](https://slack.dev/bolt-python/) - Slack bot framework
- [Flask-RESTX](https://flask-restx.readthedocs.io/) - REST API framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM

---

<p align="center">
  Made with ❤️ for the Coup community
</p>

