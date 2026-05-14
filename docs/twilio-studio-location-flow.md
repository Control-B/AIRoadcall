# Twilio Studio SMS Magic-Link Flow (Roadcall)

This guide wires Twilio Studio SMS into the existing Roadcall dispatch flow while keeping:

- **Retell** for voice/call orchestration
- **Roadcall backend** as system of record
- **GHL** for CRM/marketing workflows

## 1) What the backend now supports

### Send location SMS flow (Retell tool)
- **Endpoint:** `POST /api/location/request`
- **Auth:** `Authorization: Bearer <RETELL_BACKEND_WEBHOOK_TOKEN>`
- **Behavior:**
  - If `TWILIO_STUDIO_FLOW_SID` is set and Studio execution starts successfully:
    - returns `location_status: "studio_started"`
  - If Studio fails/unconfigured:
    - falls back to direct SMS magic-link send
    - returns `location_status: "sms_sent"`

### Poll location capture status (Retell/Studio poll)
- **Endpoint:** `POST /api/location/status`
- **Auth:** `Authorization: Bearer <RETELL_BACKEND_WEBHOOK_TOKEN>`
- **Request body:**
  ```json
  { "service_request_id": "RC-XXXX" }
  ```
- **Response statuses:**
  - `pending`: waiting for driver to share location
  - `captured`: GPS received (`lat`, `lng`, optional `city`, `state`)
  - `expired`: magic-link expired

## 2) Required backend env vars

Add to backend environment (`backend/.env`):

```dotenv
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
TWILIO_MESSAGING_SERVICE_SID=MG...        # optional but recommended
TWILIO_STUDIO_FLOW_SID=FW...              # enables Studio execution path
TWILIO_STUDIO_STATUS_CALLBACK=            # optional URL
RETELL_BACKEND_WEBHOOK_TOKEN=...
```

## 3) Parameters sent into Studio Execution

When `/api/location/request` starts a Studio execution, it passes:

- `service_request_id`
- `public_job_id`
- `secure_location_token`
- `location_url`
- `driver_name`
- `callback_number`
- `expires_at`

In Studio widgets, reference them as:

- `{{flow.data.service_request_id}}`
- `{{flow.data.location_url}}`
- `{{flow.data.driver_name}}`
- etc.

## 4) Recommended Studio flow behavior

1. **Send SMS**: "Hi {{flow.data.driver_name}}, tap to share location: {{flow.data.location_url}}"
2. **Wait** 10–15 seconds.
3. **HTTP Request** to `POST /api/location/status` with service request id.
4. **Split by** `widgets.poll_location.parsed.location_status`.
   - `captured` → send confirmation SMS and optionally trigger downstream webhook.
   - `pending` → wait + poll loop (max retries).
   - `expired` → send "link expired" + optionally call `/api/location/request` again.
5. **Exit** with clear status for observability.

## 5) Example HTTP Request widget configuration

- **Method:** `POST`
- **URL:** `https://<your-backend>/api/location/status`
- **Headers:**
  - `Authorization: Bearer <RETELL_BACKEND_WEBHOOK_TOKEN>`
  - `Content-Type: application/json`
- **Body:**
  ```json
  {
    "service_request_id": "{{flow.data.service_request_id}}"
  }
  ```

## 6) Retell integration note

Retell should keep using `request_location` (existing tool). After that, Retell can:

- continue conversation naturally,
- call status tools (or your middleware) for updates,
- proceed to matching/dispatch after `captured`.

No Retell telephony change is required for this Studio SMS path.

## 7) Security checklist

- Keep `RETELL_BACKEND_WEBHOOK_TOKEN` server-side only.
- Do not expose internal IDs in public links; use `secure_location_token` only.
- Keep short polling windows and retry caps in Studio.
- Use Twilio Messaging Service and STOP/opt-out compliant templates.

## 8) Quick verification script (manual)

1. Trigger `POST /api/location/request` for a real `service_request_id`.
2. Confirm response is `studio_started`.
3. Confirm Studio execution appears in Twilio logs.
4. Open the `location_url` on phone and share GPS.
5. Confirm `POST /api/location/status` returns `captured`.
6. Confirm dispatch proceeds in existing Roadcall flow.
