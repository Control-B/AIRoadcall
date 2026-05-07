# Roadcall.ai Retell Backend Integration

Roadcall.ai uses Retell AI only as the conversational and telephony layer. The FastAPI backend is the dispatch orchestration layer and remains the source of truth for service requests, location, payment authorization, mechanic matching, ETA, dispatch state, tracking, logging, and transcripts.

## Boundary

### Retell owns

- Inbound and outbound AI voice calls.
- Calm driver conversation and structured roadside intake.
- SMS delivery through Retell SMS or Twilio when instructed by backend.
- Speaking backend status updates in plain dispatcher language.
- Warm transfers after backend approval.
- Multilingual conversation and language continuity.

### Backend owns

- GPS processing, map provider calls, geocoding, and secure location token generation.
- Heavy-duty mechanic matching, technician capability filtering, ETA calculations, and mechanic acceptance workflow.
- Stripe manual-capture PaymentIntent creation, authorization state, expiration, and capture/cancel decisions.
- Dispatch records, Redis call/session state, PostgreSQL/Supabase persistence, tracking tokens, audit logs, and transcripts.

Retell must never expose raw `retell_call_id`, raw service request IDs, phone numbers, coordinates, or payment identifiers in public SMS URLs. Public links must use opaque backend-generated tokens.

## Required Endpoints

| Retell tool | Method | Endpoint | Backend responsibility |
| --- | --- | --- | --- |
| `create_service_request` | `POST` | `/api/calls/create-service-request` | Create dispatch record from verified safety and intake fields. |
| `request_location` | `POST` | `/api/location/request` | Generate secure GPS token, send or return SMS URL, ingest manual location fallback. |
| `get_dispatch_status` | `GET` | `/api/dispatch/status/{service_request_id}` | Return matching, payment, mechanic, ETA, cancellation, and dispatch status. |
| `request_payment` | `POST` | `/api/payment/request` | Create Stripe manual-capture authorization flow and secure payment link. |
| `confirm_dispatch` | `POST` | `/api/dispatch/confirm` | Finalize mechanic acceptance, tracking link, and dispatch confirmation. |
| `initiate_warm_transfer` | `POST` | `/api/transfer/warm` | Approve transfer, select target phone, and return whisper text. |

The local implementation in `backend/app` implements all of these endpoints with deterministic mock orchestration. It is designed for Retell tool integration testing and local Docker smoke tests, not as the final production dispatch engine.

## FastAPI Integration Notes

- Authenticate all Retell-originating requests with `Authorization: Bearer <RETELL_BACKEND_WEBHOOK_TOKEN>` plus optional HMAC signature verification.
- Store short-lived call/session state in Redis keyed by backend `service_request_id`, not by public SMS token.
- Persist normalized dispatch records, transcript pointers, payment state, location state, and mechanic acceptance events in PostgreSQL/Supabase.
- Use idempotency keys for service creation, payment request creation, dispatch confirmation, and transfer approval.
- Return only speakable confirmed information to Retell. If the backend is uncertain, return `eta_text: null`, `mechanic_company: null`, or `service_status: matching` rather than estimated guesses.
- Use structured status enums exactly as defined in `retell/roadcall-retell-flow.json` so Retell node transitions remain deterministic.

## Production Status Contract

`GET /api/dispatch/status/{service_request_id}` should return one of these statuses:

- `matching`: Backend is processing location and searching qualified providers.
- `matched`: A provider candidate exists and backend has confirmed the details returned in the response.
- `payment_required`: Dispatch cannot finalize until Stripe authorization succeeds.
- `payment_authorized`: Payment authorization succeeded; acceptance or confirmation may still be pending.
- `mechanic_confirmed`: Mechanic accepted; final dispatch confirmation can proceed.
- `dispatched`: Mechanic is confirmed and dispatch has been communicated.
- `search_continues`: Search is still active but not yet successful.
- `no_mechanic_found`: No qualified provider is currently confirmed.
- `mechanic_cancelled`: Previously matched or confirmed mechanic is no longer available; Retell restarts matching conversation.
- `failed`: Backend cannot provide a reliable status and Retell should escalate or arrange callback.

## SMS Security

- Location URL: `https://roadcall.ai/location/{{secure_location_token}}`
- Payment URL: `https://roadcall.ai/pay/{{payment_link_token}}`
- Tracking URL: `https://roadcall.ai/track/{{tracking_token}}`

Tokens should be opaque, high entropy, short-lived where appropriate, scoped to one action, revocable, and never derived from `retell_call_id`, `service_request_id`, phone number, or coordinates.

## Conversation Quality Rules

- Ask safety questions first: safe off roadway, injuries, emergency services.
- Ask concise intake questions and confirm critical details.
- Use real dispatcher phrasing: “I’m checking technician availability,” “I’m waiting on confirmed availability before I give you an ETA,” and “I found a mobile diesel mechanic capable of handling that issue.”
- Avoid generic filler like “I understand your concern” unless paired with a concrete next action.
- Never promise service, availability, price, ETA, dispatch, or mechanic arrival unless backend confirms it.

## Warm Transfer Requirements

Warm transfer is allowed only when all of the following are true:

- Backend returned `mechanic_confirmed: true`.
- Backend returned `transfer_approved: true`.
- Backend returned a valid `transfer_phone`.
- Driver requested direct coordination or backend policy requires escalation.

Retell should provide a concise whisper before connecting:

> You are receiving a driver with a coolant leak on Interstate 75 near mile marker 240. ETA already communicated to driver.

The generated whisper should include driver name, callback, equipment, load status, problem, location summary, ETA already communicated, and service request reference for internal users only.

## Failure Handling

- No mechanic found: explain shortage professionally, offer callback, keep search active.
- SMS failed: collect highway/interstate, mile marker, nearest exit, city/state, truck stop, landmark, and direction of travel.
- GPS unavailable: continue with manual location if sufficient.
- Mechanic cancelled: restart matching flow automatically and do not blame provider.
- Payment failed: resend secure payment link if requested; never collect card details by voice.
- Backend timeout: retry once, then transfer to human dispatcher or arrange callback.

## Optional LiveKit Usage

LiveKit can be added later for advanced realtime orchestration, supervisor whisper/barge-in, multi-party coordination, or streaming telemetry. It should not replace backend dispatch authority or Retell’s call-control responsibilities unless explicitly designed.