# Roadcall.ai Real-Time Dispatch Architecture

This document defines the production architecture for Roadcall.ai as an AI-powered roadside dispatch marketplace with Uber-style session tracking, live GPS, mechanic matching, payment gating, and admin oversight.

## Current Repo Baseline

- **Frontend:** Next.js 14 App Router, TypeScript, TailwindCSS, Mapbox GL JS, Stripe client libraries.
- **Backend:** FastAPI, async SQLAlchemy, Alembic, PostgreSQL, Retell AI webhooks/tools, Twilio SMS helpers, Stripe manual-capture payment flows.
- **Data:** DigitalOcean PostgreSQL already contains the private `mechanics` directory and matching fields such as services, vehicle types, coordinates, mobile roadside support, emergency support, radius, and priority.
- **Existing dispatch pieces:** `roadside_incidents`, `location_capture_sessions`, `/api/go/dispatch`, `/api/go/status`, `/api/roadside/match-mechanic`, `/api/dispatch/*`, Retell tool routes, Mapbox reverse geocoding, travel-time estimation, and live map components.
- **Known gap:** `/go` currently caches status in memory by phone. That helps Retell polling, but it is not durable, not multi-instance safe, and does not create a single source-of-truth session joining call ID, caller phone, GPS token, matching results, payment state, and mechanic assignment.

## Product Model

Roadcall should behave like a roadside dispatch marketplace:

1. A caller reaches Roadcall by phone, website, fleet portal, or SMS link.
2. A unified dispatch session is created immediately.
3. The AI agent collects only the minimum required facts: location, problem, vehicle type, and callback identity.
4. GPS capture updates the same live dispatch session, not a detached browser cache.
5. The matching engine ranks verified mechanics by location, service compatibility, vehicle support, mobile capability, 24/7 support, radius, priority, distance, and ETA.
6. Dispatchers/admins see the session update live on a map and can override AI decisions.
7. Mechanics receive a limited lead preview first; exact caller location is revealed only after the required lead fee or authorization succeeds.
8. Every state transition is persisted, auditable, and broadcast in real time.

## Core Principle

`dispatch_sessions` becomes the single orchestration record. Phone calls, Retell sessions, Twilio CallSids, GPS links, `/go` submissions, Stripe payments, mechanic matches, mechanic offers, and admin actions attach to this record.

## Target Database Schema

### `dispatch_sessions`

Primary state machine for each roadside event.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | Internal primary key. |
| `public_code` | varchar unique | Short fallback code for phone/manual lookup, for example `RC-48291`. |
| `status` | enum/text | `created`, `intake`, `awaiting_location`, `matching`, `matched`, `offer_sent`, `payment_required`, `payment_authorized`, `assigned`, `en_route`, `on_site`, `completed`, `cancelled`, `manual_review`. |
| `source` | varchar | `retell`, `twilio`, `web`, `admin`, `fleet`, `api`. |
| `caller_phone_hash` | varchar indexed | Search-safe phone key. Store normalized phone encrypted or separately protected if needed. |
| `caller_phone_last4` | varchar | Admin display without exposing full phone by default. |
| `caller_name` | varchar nullable | Caller-provided. |
| `retell_call_id` | varchar indexed nullable | Retell call reference. |
| `twilio_call_sid` | varchar indexed nullable | Twilio CallSid. |
| `active_location_token_id` | UUID nullable | Current GPS token/session. |
| `problem_type` | varchar nullable | Normalized issue: tire, engine, battery, fuel, tow, lockout, reefer, trailer, other. |
| `problem_description` | text nullable | Caller transcript summary. |
| `vehicle_type` | varchar nullable | car, pickup, box truck, semi, trailer, RV, fleet vehicle. |
| `vehicle_description` | varchar nullable | Free text vehicle details. |
| `lat` / `lng` | float nullable | Current breakdown coordinates. |
| `location_accuracy_m` | float nullable | Browser GPS accuracy. |
| `address` | text nullable | Reverse-geocoded address. |
| `city` / `state` | varchar nullable | Normalized location. |
| `location_source` | varchar nullable | `browser_gps`, `sms_link`, `manual_text`, `retell_transcript`, `admin`, `mapbox`. |
| `location_captured_at` | timestamptz nullable | Latest verified location time. |
| `selected_mechanic_id` | UUID nullable | Final assigned mechanic. |
| `selected_offer_id` | UUID nullable | Accepted assignment offer. |
| `payment_status` | varchar | `not_required`, `required`, `pending`, `authorized`, `captured`, `failed`, `refunded`. |
| `stripe_payment_intent_id` | varchar nullable | Stripe authorization/capture reference. |
| `metadata` | jsonb | Provider payloads, user agent, confidence, fallbacks. |
| `created_at` / `updated_at` | timestamptz | Standard timestamps. |

Recommended indexes:

- `retell_call_id`, `twilio_call_sid`, `public_code` unique/lookup indexes.
- `caller_phone_hash, created_at DESC` for phone fallback lookup.
- `status, updated_at DESC` for dispatch board.
- PostGIS geography index later for location filtering if PostGIS is enabled.

### `dispatch_location_events`

Append-only timeline of location updates.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | Event ID. |
| `dispatch_session_id` | UUID FK | Parent session. |
| `lat` / `lng` | float | Coordinates. |
| `accuracy_m` | float nullable | GPS accuracy. |
| `source` | varchar | browser, SMS link, admin, Retell text, Mapbox reverse geocode. |
| `raw_payload` | jsonb | Browser/API payload. |
| `created_at` | timestamptz | Event time. |

### `dispatch_match_results`

Stores each matching run and the ranked candidates shown to AI/admin.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | Match run ID. |
| `dispatch_session_id` | UUID FK | Parent session. |
| `request_context` | jsonb | Location/problem/vehicle inputs. |
| `search_level` | varchar | exact city, nearby city, state fallback, major vendor fallback. |
| `status` | varchar | matched, needs_more_info, manual_dispatch_required. |
| `candidates` | jsonb | Top ranked candidates with masked sensitive fields for non-admin views. |
| `selected_mechanic_id` | UUID nullable | Candidate selected from this run. |
| `created_at` | timestamptz | Match time. |

### `mechanic_offers`

Tracks marketplace lead offers and mechanic acceptance.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | Offer ID. |
| `dispatch_session_id` | UUID FK | Parent session. |
| `mechanic_id` | UUID FK | Candidate provider. |
| `status` | varchar | `queued`, `sent`, `viewed`, `payment_pending`, `accepted`, `declined`, `expired`, `cancelled`. |
| `preview_payload` | jsonb | Problem, city/state, vehicle, approximate distance. No exact coordinates before payment. |
| `exact_payload_revealed_at` | timestamptz nullable | Set after payment authorization/success. |
| `stripe_checkout_session_id` | varchar nullable | Lead fee checkout. |
| `expires_at` | timestamptz | Offer expiration. |
| `created_at` / `updated_at` | timestamptz | Standard timestamps. |

### `dispatch_session_events`

Append-only audit and realtime event bus table. The existing provisioning table `dispatch_events` remains separate; production session orchestration should use `dispatch_session_events` to avoid schema conflicts.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | Event ID. |
| `dispatch_session_id` | UUID FK | Parent session. |
| `event_type` | varchar indexed | `session.created`, `location.updated`, `match.completed`, `offer.sent`, `payment.authorized`, `mechanic.assigned`, etc. |
| `actor_type` | varchar | `ai`, `caller`, `admin`, `mechanic`, `stripe`, `system`. |
| `actor_id` | varchar nullable | User/admin/mechanic/system reference. |
| `payload` | jsonb | Redacted event details. |
| `created_at` | timestamptz | Event time. |

### Extensions to Existing Tables

- **`location_capture_sessions`:** add `dispatch_session_id`, `token_hash`, `used_at`, `revoked_at`, `last_ip_hash`, `last_user_agent_hash`.
- **`roadside_incidents`:** keep as business incident record or migrate into `dispatch_sessions`; during transition add nullable `dispatch_session_id`.
- **`jobs`:** add nullable `dispatch_session_id` for existing payment/support flows.
- **`mechanics`:** keep private; expose only through role-scoped views and redacted API responses.

## Backend Architecture

### Services

Recommended service modules:

- `app/services/dispatch_session_service.py` — create, resolve, update, and transition sessions.
- `app/services/location_session_service.py` — signed GPS tokens, token validation, location writes, reverse geocoding.
- `app/services/realtime_event_service.py` — persist `dispatch_session_events` and broadcast WebSocket/Supabase events.
- `app/services/mechanic_offer_service.py` — offer queueing, mechanic lead preview, acceptance, expiration.
- `app/services/roadside_matching_service.py` — existing scoring engine; keep as the private ranking authority.
- `app/services/payment_service.py` — existing Stripe logic extended for lead fees and exact-location reveal.
- `app/services/ai_dispatch_orchestrator.py` — Retell-safe orchestration layer that returns short, verified status summaries.

### API Routes

New routes should live under `backend/app/api/routes/dispatch_sessions.py` and avoid making raw mechanic search public.

#### Session Creation

`POST /api/dispatch/create-session`

Auth: Retell backend token, Twilio webhook signature, admin auth, or internal API key.

Request:

```json
{
  "source": "retell",
  "retell_call_id": "call_123",
  "twilio_call_sid": "CA123",
  "caller_phone": "+18135551212",
  "caller_name": "Sam",
  "problem_description": "flat tire on a semi",
  "vehicle_type": "semi"
}
```

Response:

```json
{
  "dispatch_session_id": "uuid",
  "public_code": "RC-48291",
  "status": "awaiting_location",
  "location_url": "https://roadcall.ai/go?t=signed-token",
  "expires_at": "2026-01-01T12:30:00Z"
}
```

Behavior:

- Idempotently finds an active session by `retell_call_id`, `twilio_call_sid`, or recent `caller_phone_hash`.
- Creates a signed location token tied to `dispatch_session_id`.
- Emits `session.created` and `location.requested`.

#### Location Update

`POST /api/dispatch/update-location`

Auth: signed short-lived GPS token from `/go?t=...` or admin auth.

Request:

```json
{
  "token": "signed-token",
  "latitude": 28.0395,
  "longitude": -81.9498,
  "accuracy_m": 18,
  "source": "browser_gps"
}
```

Behavior:

- Validates token signature, expiry, audience, and dispatch session.
- Writes `dispatch_location_events`.
- Updates `dispatch_sessions.lat/lng/city/state/address` after Mapbox reverse geocoding.
- Runs `RoadsideMatchingService.match_mechanic` when enough problem and vehicle context exists.
- Persists `dispatch_match_results`.
- Broadcasts `location.updated` and `match.completed`.

#### Session Lookup for AI

`GET /api/dispatch/session-status/{dispatch_session_id}`

Auth: Retell backend token, admin auth, or internal key.

Returns a short, AI-safe summary:

```json
{
  "status": "matched",
  "location_captured": true,
  "city": "Lakeland",
  "state": "FL",
  "best_match": {
    "company_name": "Verified Truck Repair",
    "eta_text": "about 28 minutes",
    "phone_available": true
  },
  "say": "I found Verified Truck Repair near Lakeland with an estimated arrival of about 28 minutes. I’m confirming availability now."
}
```

Do not return full mechanic exports or raw directory data to browser-public contexts.

#### Case Code Fallback

`POST /api/dispatch/link-case-code`

Auth: public but rate-limited, protected by public code + caller phone last 4.

Purpose: lets a caller who cannot open the SMS link enter `RC-48291` on `roadcall.ai/go` and attach GPS to the correct live session.

#### Admin Session APIs

- `GET /api/admin/dispatch/sessions?status=active`
- `GET /api/admin/dispatch/sessions/{id}`
- `POST /api/admin/dispatch/sessions/{id}/override-location`
- `POST /api/admin/dispatch/sessions/{id}/select-mechanic`
- `POST /api/admin/dispatch/sessions/{id}/send-offer`
- `POST /api/admin/dispatch/sessions/{id}/cancel`

Auth: Clerk admin session or existing admin token until Clerk migration is complete.

#### Mechanic Offer APIs

- `POST /api/mechanic/offers/{offer_id}/checkout` — create Stripe lead fee checkout.
- `GET /api/mechanic/offers/{offer_token}` — redacted preview before payment.
- `POST /api/mechanic/offers/{offer_token}/accept` — only after payment authorization/success.
- `GET /api/mechanic/jobs/{offer_token}` — exact location after reveal.

## Realtime Architecture

### Recommended First Production Step: FastAPI WebSockets

Use first-party WebSockets because the backend is already FastAPI and can enforce existing auth.

- `WS /api/realtime/dispatch/{dispatch_session_id}` for caller support page and admin detail page.
- `WS /api/realtime/admin/dispatch` for the admin operations board.
- Events are persisted to `dispatch_session_events` before broadcast.
- WebSocket messages contain redacted payloads based on role: caller, admin, mechanic, AI, system.

### Supabase Realtime Option

If moving Postgres to Supabase, broadcast from `dispatch_session_events` using row-level security and Realtime channels:

- `dispatch-session:{id}` for one session.
- `admin-dispatch-board:{org_id}` for operations.
- `mechanic-offer:{offer_id}` for a provider.

Supabase is useful when you want managed realtime fanout, but keep FastAPI as the policy/orchestration authority.

### Event Types

- `session.created`
- `intake.updated`
- `location.requested`
- `location.updated`
- `location.failed`
- `match.started`
- `match.completed`
- `match.manual_review`
- `offer.sent`
- `offer.viewed`
- `payment.required`
- `payment.authorized`
- `payment.failed`
- `mechanic.assigned`
- `mechanic.en_route`
- `mechanic.on_site`
- `session.completed`
- `session.cancelled`

## Frontend Architecture

### Public Caller Pages

- `frontend/src/app/go/page.tsx`
  - Support `?t=SIGNED_TOKEN` as the primary flow.
  - Also support manual fallback with case code + phone last 4.
  - Captures GPS, posts to `/api/dispatch/update-location`, and subscribes to the session WebSocket.
- `frontend/src/app/support/[token]/page.tsx`
  - Can remain for legacy magic links, but should eventually route through the unified session token.
- `frontend/src/app/pay/[token]/page.tsx`
  - Stripe payment authorization page for caller-side payment if needed.

### Admin Pages

- `frontend/src/app/admin/dispatch/page.tsx`
  - Live operations board: active sessions, status, city/state, age, issue, payment state, assigned mechanic.
- `frontend/src/app/admin/dispatch/[id]/page.tsx`
  - Detail page with live map, event timeline, transcript summary, matching candidates, admin override tools.
- `frontend/src/app/admin/mechanics/page.tsx`
  - Keep existing directory viewer protected. Add “dispatch performance” and “offer acceptance” columns later.

### Mechanic Pages

- `frontend/src/app/mechanic/offers/[token]/page.tsx`
  - Redacted lead preview: approximate area, vehicle, problem, estimated distance, fee.
  - Stripe checkout to unlock exact location.
- `frontend/src/app/mechanic/jobs/[token]/page.tsx`
  - Exact location, caller contact rules, directions, status update buttons.

### Frontend State

Use a small dispatch state store:

- `frontend/src/lib/dispatch-api.ts` — typed REST client.
- `frontend/src/lib/dispatch-realtime.ts` — WebSocket/Supabase client.
- `frontend/src/stores/dispatch-session-store.ts` — Zustand or React Context.
- `frontend/src/components/dispatch/live-dispatch-map.tsx` — Mapbox session map.
- `frontend/src/components/dispatch/match-candidate-card.tsx` — candidate rendering with role-safe fields.
- `frontend/src/components/dispatch/event-timeline.tsx` — live timeline from `dispatch_session_events`.

## Mapbox Integration

Backend responsibilities:

- Reverse geocode browser GPS into city, state, address, and place name.
- Compute ETA using Mapbox Matrix through the existing travel-time service.
- Store Mapbox result metadata in `dispatch_location_events.raw_payload` or session metadata.
- Fall back to Haversine distance and coordinate-based state inference if Mapbox fails.

Frontend responsibilities:

- Render caller and mechanic markers with Mapbox GL JS.
- Show route polyline only to admin/caller after mechanic assignment.
- Do not reveal exact caller coordinates to mechanic preview pages before payment unlock.

## Stripe Flow

### Caller Authorization Flow

Use existing manual-capture PaymentIntent pattern when Roadcall needs caller authorization before dispatch finalization.

1. Backend creates PaymentIntent with manual capture.
2. Caller completes secure Stripe flow on `roadcall.ai/pay/[token]`.
3. Stripe webhook updates `dispatch_sessions.payment_status`.
4. Backend emits `payment.authorized`.
5. AI/admin continues dispatch.

### Mechanic Lead Fee Flow

For the marketplace model:

1. Roadcall sends mechanic an offer preview without exact location.
2. Mechanic clicks offer link and sees approximate area/problem/vehicle.
3. Mechanic pays lead fee through Stripe Checkout or PaymentIntent.
4. Stripe webhook marks offer `payment_authorized` or `accepted`.
5. Exact caller location and contact instructions become visible.
6. Dispatch session emits `mechanic.assigned` once admin/AI confirms assignment.

## AI Orchestration Flow

Retell should be the conversational layer only. FastAPI remains the source of truth.

### Retell Call Start

1. Retell webhook calls `/api/dispatch/create-session` with `retell_call_id`, `twilio_call_sid`, and caller phone when available.
2. Backend returns `dispatch_session_id`, `public_code`, and `location_url`.
3. AI says one short prompt, for example: “I can help. What city and state are you in?”

### Location Collection

- If caller has smartphone: AI sends or directs them to `roadcall.ai/go?t=SIGNED_TOKEN`.
- If SMS fails: AI gives `roadcall.ai/go` plus public code.
- If phone cannot use browser: AI collects city/state/landmark and updates session through the backend.

### Matching

1. Once location + problem + vehicle type exist, backend runs matching.
2. AI polls `/api/dispatch/session-status/{id}` every 8-10 seconds.
3. AI only says data returned in the `say` field or verified response fields.
4. AI never invents ETA, provider name, location, or availability.

### Prompt Rules

- Ask one question at a time.
- Keep responses short and dispatcher-like.
- Do not ask for email, insurance, license plate, payment card details, or exact address before matching.
- Do not expose internal database counts or raw directory details.
- Escalate to manual dispatch if matching fails, GPS fails, or the caller is unsafe.

## Security Model

- **Mechanic data:** private by default; no unauthenticated list/search/RAG endpoint.
- **Admin:** migrate to Clerk; until then, keep server-side admin login and `X-Admin-Key` protected endpoints.
- **AI/Retell:** use `Authorization: Bearer RETELL_BACKEND_WEBHOOK_TOKEN`; never expose this token to browsers.
- **GPS tokens:** signed, short-lived, scoped to a single dispatch session, stored hashed server-side, revocable, one active token per session unless explicitly regenerated.
- **Phone numbers:** normalize for matching, store hashes for lookup, minimize full phone exposure in UI.
- **Rate limits:** apply to `/go`, case-code lookup, location update, offer preview, and login.
- **Audit:** every state transition writes `dispatch_session_events` before broadcast.
- **PII redaction:** role-based serializers for caller/admin/mechanic/AI responses.
- **Payment:** never collect card numbers by voice; only Stripe-hosted/client-confirmed flows.

## Deployment Architecture

### DigitalOcean First

- Keep existing DigitalOcean App Platform services.
- Add Redis if using multi-instance FastAPI WebSockets or background offer queues.
- Keep DigitalOcean Managed Postgres for now.
- Use DO secrets for Mapbox, Stripe, Retell, Twilio, Clerk, JWT signing keys.

### Supabase Option

- Move Postgres to Supabase only when ready to use Supabase Realtime/RLS intentionally.
- Keep FastAPI as the only writer for sensitive dispatch/mechanic/payment state.
- Use Supabase Realtime channels for frontend fanout, not direct unrestricted table access.

### Workers

Add background workers for:

- Offer expiration and escalation.
- Mechanic SMS/email/push notifications.
- Payment timeout handling.
- Retell transcript summarization and call-finalization events.
- Email enrichment jobs for mechanics, isolated from dispatch traffic.

## Production Folder Structure

Backend additions:

```text
backend/app/api/routes/dispatch_sessions.py
backend/app/api/routes/realtime.py
backend/app/api/routes/mechanic_offers.py
backend/app/models/dispatch_session.py
backend/app/models/dispatch_event.py
backend/app/models/dispatch_match_result.py
backend/app/models/mechanic_offer.py
backend/app/schemas/dispatch_session.py
backend/app/schemas/realtime.py
backend/app/schemas/mechanic_offer.py
backend/app/services/dispatch_session_service.py
backend/app/services/location_session_service.py
backend/app/services/realtime_event_service.py
backend/app/services/mechanic_offer_service.py
backend/app/services/ai_dispatch_orchestrator.py
backend/tests/test_dispatch_sessions.py
backend/tests/test_dispatch_location_tokens.py
backend/tests/test_realtime_dispatch_events.py
backend/tests/test_mechanic_offer_payment_gate.py
```

Frontend additions:

```text
frontend/src/app/admin/dispatch/page.tsx
frontend/src/app/admin/dispatch/[id]/page.tsx
frontend/src/app/mechanic/offers/[token]/page.tsx
frontend/src/app/mechanic/jobs/[token]/page.tsx
frontend/src/components/dispatch/live-dispatch-map.tsx
frontend/src/components/dispatch/dispatch-session-panel.tsx
frontend/src/components/dispatch/match-candidate-card.tsx
frontend/src/components/dispatch/event-timeline.tsx
frontend/src/lib/dispatch-api.ts
frontend/src/lib/dispatch-realtime.ts
frontend/src/stores/dispatch-session-store.ts
```

## Implementation Phases

### Phase 1 — Durable Session Foundation

- Add `dispatch_sessions`, `dispatch_session_events`, `dispatch_location_events`, and `dispatch_match_results` migrations/models.
- Add `DispatchSessionService` and event writer.
- Implement `/api/dispatch/create-session`, `/api/dispatch/update-location`, and `/api/dispatch/session-status/{id}`.
- Update `/api/go/dispatch` to write durable sessions instead of only `_DISPATCH_CACHE`.
- Update Retell tools to use `dispatch_session_id` first, phone fallback second.

### Phase 2 — Live Operations Board

- Add WebSocket or Supabase Realtime broadcasting from `dispatch_session_events`.
- Build `/admin/dispatch` and `/admin/dispatch/[id]`.
- Add Mapbox live session map and event timeline.
- Add admin override for location, selected mechanic, and manual review.

### Phase 3 — Mechanic Marketplace Offers

- Add `mechanic_offers` model and APIs.
- Add redacted mechanic offer page.
- Add Stripe lead fee checkout and webhook state updates.
- Reveal exact caller location only after payment success/authorization.

### Phase 4 — AI Orchestration Upgrade

- Add `ai_dispatch_orchestrator.py` for Retell-safe summaries.
- Update Retell flow/tool definitions to create sessions at call start and poll by session ID.
- Ensure AI says only backend-confirmed provider/ETA/payment/location status.
- Add fallback case-code prompts.

### Phase 5 — Hardening and Scale

- Add Clerk admin auth.
- Add rate limiting and token replay protection.
- Add Redis-backed realtime fanout/queues if multiple backend instances are enabled.
- Add metrics: match latency, GPS capture rate, call-to-dispatch time, payment conversion, mechanic acceptance rate.
- Add data retention and PII redaction jobs.

## Test Plan

- `test_dispatch_create_session_idempotent_by_call_sid`
- `test_dispatch_create_session_idempotent_by_phone_recent_window`
- `test_location_token_updates_correct_session`
- `test_location_token_rejects_expired_or_wrong_session`
- `test_update_location_runs_matching_when_context_complete`
- `test_retell_status_returns_ai_safe_summary`
- `test_case_code_links_location_to_existing_session`
- `test_mechanic_preview_hides_exact_location_before_payment`
- `test_stripe_webhook_reveals_location_after_payment`
- `test_realtime_event_written_before_broadcast`
- `test_public_mechanic_directory_stays_locked_down`

## Acceptance Criteria

- A live Retell call, `/go?t=...` GPS capture, admin dashboard, mechanic matching, payment state, and final assignment all reference the same `dispatch_session_id`.
- Refreshing or scaling backend instances does not lose dispatch status.
- AI can poll live backend state and speak confirmed updates while the caller remains on the phone.
- Admin can watch every active roadside session on a live board and intervene manually.
- Mechanics cannot see exact caller coordinates until the payment/authorization rule passes.
- Private mechanic directory data remains unavailable to unauthenticated users.