# AI Roadside Support (AIRoadcall)

AI-powered roadside assistance dispatch system. A driver calls an AI phone agent, receives an SMS magic link, confirms location, authorizes payment, and tracks their mechanic in real time.

## Architecture

```
Driver Phone Call → LiveKit Cloud AI → FastAPI Backend → SMS Magic Link
                                      ↓
                               Next.js Frontend ← Driver opens link
                                      ↓
                               FastAPI Backend → Stripe, Mechanic Dispatch
                                      ↓
                               Live Tracking via Mapbox
```

**Separation of concerns:**
- **Next.js** — Driver-facing UI only (magic link web app)
- **FastAPI** — All business logic, orchestration, payment, dispatch
- **Agent Worker** — LiveKit AI telephony (separate process, crash-isolated)
- **Postgres** — Single shared database

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12+, SQLAlchemy 2.0, Pydantic v2 |
| AI Agent | LiveKit Agents SDK (all-in-one: LLM, voice, SIP) |
| Database | PostgreSQL 16, Prisma ORM (frontend), Alembic (backend) |
| Payments | Stripe (authorization holds with manual capture) |
| Maps | Mapbox GL JS |
| AI Telephony | LiveKit Cloud (SIP trunking + AI agents) |
| SMS | Twilio |
| Packaging | uv (Python), npm (Node.js) |
| Infrastructure | Docker Compose (4 microservices) |
| Data Pipeline | Apify (bulk scraping), Tavily (real-time enrichment) |

## Project Structure

```
AIRoadcall/
├── docker-compose.yml           # Full stack: postgres, backend, agent, frontend
├── .env.example                 # All environment variables (copy to .env)
│
├── backend/                     # FastAPI orchestration service
│   ├── Dockerfile
│   ├── pyproject.toml           # Dependencies managed by uv
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── core/                # Config, database, security, logging
│   │   ├── api/
│   │   │   ├── deps.py          # Dependency injection (DB, token validation)
│   │   │   └── routes/          # All API route handlers
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # Business logic layer
│   │   │   ├── apify_service.py  # Bulk mechanic data scraping
│   │   │   ├── tavily_service.py # Real-time data enrichment
│   │   │   └── ...              # Job, payment, dispatch, tracking services
│   │   ├── enums/               # Job, payment, dispatch, tracking status enums
│   │   └── utils/               # Geo, time, idempotency utilities
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test structure
│   ├── seed.py                  # Seed data script
│   └── .env.example
│
├── agent/                       # LiveKit AI agent worker (separate process)
│   ├── Dockerfile
│   ├── pyproject.toml           # Dependencies managed by uv
│   └── agent_worker.py          # Inbound intake + outbound dispatch agents
│
└── frontend/                    # Next.js driver-facing web app
    ├── Dockerfile
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx       # Root layout
    │   │   ├── page.tsx         # Landing page
    │   │   ├── dev/
    │   │   │   └── api-tester/  # API testing dashboard
    │   │   └── support/
    │   │       └── [token]/
    │   │           └── page.tsx # Main multi-step driver flow
    │   ├── components/
    │   │   ├── ui/              # shadcn/ui components
    │   │   ├── step-indicator.tsx
    │   │   └── steps/           # Step components
    │   └── lib/
    │       ├── api-client.ts    # FastAPI REST client
    │       ├── prisma.ts        # Prisma client singleton
    │       ├── stripe.ts        # Stripe client
    │       └── utils.ts         # Utility functions
    ├── prisma/
    │   ├── schema.prisma        # Database schema
    │   └── seed.ts              # Seed data
    ├── package.json
    └── .env.example
```

## Driver Flow

1. **AI Phone Call** → Driver calls, LiveKit Cloud AI agent collects issue details
2. **Magic Link SMS** → Backend creates job, sends secure link via SMS
3. **Open Link** → Driver opens `/support/[token]` on their phone
4. **Step 1: Summary** → Review issue details from the AI call
5. **Step 2: Location** → Share precise GPS location via browser
6. **Step 3: Payment** → Authorize a card hold (not charged yet)
7. **Step 4: Dispatch** → System ranks and calls mechanics
8. **Step 5: Tracking** → Watch mechanic approach on live map

## Security

- Magic link tokens are JWT-signed with expiration
- Raw job IDs are never exposed to the driver
- Every driver-facing API request validates the token
- Stripe webhook signatures are verified
- Only safe fields are returned to the frontend

## Getting Started

### Quick Start (Docker)

The fastest way to run the full stack:

```bash
# 1. Clone and configure
git clone <repo>
cd AIRoadcall
cp .env.example .env
# Edit .env with your API keys (Stripe, LiveKit, Twilio, etc.)

# 2. Start everything
docker compose up -d

# 3. Run database migrations
docker compose exec backend alembic revision --autogenerate -m "initial"
docker compose exec backend alembic upgrade head

# 4. Seed sample data
docker compose exec backend python seed.py
```

Services:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **API Tester:** http://localhost:3000/dev/api-tester
- **Postgres:** localhost:5432

Useful commands:
```bash
# Rebuild a single service after code changes
docker compose up -d --build backend

# Tail logs for a specific service
docker compose logs -f agent

# Restart just the agent if it crashes
docker compose restart agent

# Stop everything
docker compose down

# Stop and wipe the database volume
docker compose down -v
```

### Local Development (without Docker)

#### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+
- PostgreSQL database (local or Render)

#### Backend Setup

```bash
cd backend

# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your database URL and API keys

# Run migrations
uv run alembic revision --autogenerate -m "initial"
uv run alembic upgrade head

# Seed sample data
uv run python seed.py

# Start the server
uv run uvicorn app.main:app --reload --port 8000
```

#### Agent Worker Setup

```bash
cd agent

# Install dependencies
uv sync

# Start the agent worker (connects to LiveKit Cloud)
LIVEKIT_API_KEY=xxx LIVEKIT_API_SECRET=xxx LIVEKIT_URL=wss://... \
  uv run python agent_worker.py start
```

#### Frontend Setup

```bash
cd frontend


# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your keys

# Generate Prisma client
npx prisma generate

# Start dev server
npm run dev
```

## DO Spaces Media (Videos + Images)

Use DigitalOcean Spaces for large media files and keep fast deploys.

1. Configure AWS-compatible credentials for Spaces in your shell (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
2. Export Spaces settings:

```bash
export DO_SPACES_BUCKET="your-bucket"
export DO_SPACES_REGION="nyc3"
export DO_SPACES_ENDPOINT="https://nyc3.digitaloceanspaces.com"
```

3. Sync media files:

```bash
bash scripts/sync_media_to_spaces.sh
```

4. Point the frontend to Spaces/CDN:

```bash
export NEXT_PUBLIC_MEDIA_BASE_URL="https://your-bucket.nyc3.digitaloceanspaces.com"
```

The app uses local fallbacks when `NEXT_PUBLIC_MEDIA_BASE_URL` is not set.

### Verify

- Backend health: http://localhost:8000/health
- Backend API docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- API Tester: http://localhost:3000/dev/api-tester
- Test magic link: http://localhost:3000/support/seed-token-tracking-test

## API Endpoints

### Jobs (driver-facing, token-validated)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/jobs` | Create job (from LiveKit) |
| GET | `/api/jobs/{token}` | Get job by magic token |
| POST | `/api/jobs/{token}/location` | Save driver GPS |
| GET | `/api/jobs/{token}/status` | Poll job status |
| POST | `/api/jobs/{token}/payment-intent` | Create Stripe hold |
| POST | `/api/jobs/{token}/payment-confirm` | Confirm payment auth |
| GET | `/api/jobs/{token}/tracking` | Get tracking data |

### Dispatch (internal)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dispatch/{job_id}/start` | Begin mechanic matching |
| POST | `/api/dispatch/{job_id}/next` | Dispatch next mechanic |
| POST | `/api/dispatch/{job_id}/mechanic-response` | Record response |

### Mechanics (internal)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/mechanics` | Create/update mechanic |
| POST | `/api/mechanics/{id}/location` | Update GPS location |

### Webhooks
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/webhooks/stripe` | Stripe payment events |
| POST | `/api/webhooks/livekit` | LiveKit Cloud call events |

### Data Pipeline
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/pipeline/scrape` | Start Apify Google Maps scrape |
| GET | `/api/pipeline/scrape/{run_id}` | Check scrape run status |
| POST | `/api/pipeline/scrape/{run_id}/import` | Import results to DB |
| POST | `/api/pipeline/enrich` | Enrich mechanics via Tavily |
| GET | `/api/pipeline/stats` | Pipeline & DB statistics |

## Business Rules

1. Driver must submit location before payment
2. Payment must be authorized before dispatch
3. Mechanics are ranked by distance, capability match, rating
4. Dispatch attempts are always logged
5. If a mechanic declines/times out, system moves to next
6. First accepted mechanic becomes assigned
7. Mechanic location updates trigger en-route status
8. Proximity within threshold triggers arrived status
9. Full audit trail for all major transitions

## Environment Variables

See `.env.example` for all required variables.

**Key API keys needed:**
- **LiveKit** — All-in-one AI telephony (LLM, voice, phone numbers). ONE key handles everything.
- **Stripe** — Payment authorization holds
- **Mapbox** — Live tracking maps
- **Apify** — Bulk mechanic data scraping
- **Tavily** — Real-time mechanic verification
- **Twilio** — SMS magic links

> **Note:** No separate OpenAI key is needed. LiveKit Cloud includes LLM and voice services.