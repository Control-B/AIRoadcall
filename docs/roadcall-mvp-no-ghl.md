# Roadcall MVP — No GHL Core Dependency

Roadcall MVP is the system of record for roadside matching and dispatch. GoHighLevel can remain in the codebase for later CRM/marketing automation, but it is not required for the MVP dispatch path.

## MVP Positioning

Roadcall is an AI-powered roadside dispatch and mechanic matching platform for stranded drivers, fleets, and service providers.

## Core MVP Flow

1. Driver/caller contacts Roadcall or a dispatcher.
2. Dispatcher creates a Roadcall job and receives a public case code, for example `RC-A1B2C3D4`.
3. If A2P/SMS is unavailable, the dispatcher tells the caller to open `https://roadcall.ai/go`.
4. Caller enters the case code.
5. Roadcall opens the secure support page for that job.
6. Caller shares browser GPS location.
7. If GPS fails or permission is denied, caller enters an address, highway exit, city/state, landmark, or truck stop.
8. Roadcall geocodes the manual location and saves coordinates to the job.
9. Roadcall matches nearby mechanics/service providers and dispatches through the Roadcall backend.
10. Driver and dispatcher track status in Roadcall.

## What Roadcall Owns

- Job creation and case codes
- Driver/caller location capture
- Mechanic database and matching logic
- Dispatch status and mechanic assignment
- Stripe billing/payment authorization
- Admin dashboard and operational visibility

## What Is Deferred

- GHL as CRM/workflow automation
- AI telephony for mechanics and shops
- Marketing nurture workflows
- Provider CRM automations

## A2P Waiting-Period Location Fallback

Until SMS/A2P approval is complete, the caller-location flow should be:

```text
Dispatcher: Go to roadcall.ai/go and enter this code: RC-XXXXXXX.
Caller: Enters code and shares GPS in the browser.
Fallback: If GPS is blocked, caller enters nearest address/exit/landmark/city/state.
```

This keeps location capture inside Roadcall and avoids depending on SMS, GHL, or AI telephony for the MVP.

## Live Call Rule

The agent/dispatcher should not end the call just because a text, link, or case code was given. Stay on the line until:

- A mechanic is confirmed or dispatched by backend status.
- The caller explicitly says they are done and wants to hang up.
- The caller hangs up.
- The caller reports injury, fire, or immediate danger and is told to call 911.

## Location Priority

Use location methods in this order:

1. **Fleet tracker lookup** — if caller is with a fleet and has a company name plus truck/trailer/unit number.
2. **Website code fallback** — caller opens `https://roadcall.ai/go` and enters the Roadcall case code while staying on the call.
3. **Direct SMS** — use Twilio/Telnyx only if available; do not depend on it while A2P is pending.
4. **Manual location** — highway, exit, mile marker, direction, nearest truck stop, landmark, city, and state.

## Twilio Readiness Check

Dry-run config check:

```bash
cd backend
.venv/bin/python scripts/check_twilio_sms.py
```

Dry-run the production local sender without sending:

```bash
cd backend
.venv/bin/python scripts/check_twilio_sms.py --from-number +18134524889
```

Live test, only when you have permission to text the destination number:

```bash
cd backend
.venv/bin/python scripts/check_twilio_sms.py --from-number +18134524889 --to +15551234567 --send
```
