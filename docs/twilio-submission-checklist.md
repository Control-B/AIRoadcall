# Twilio Submission Checklist (One-Pass Paste Order)

Use this page while completing both Twilio forms.
Reference source: `docs/twilio-registration-fix-pack.md`.

---

## A) Toll-Free Resubmission (for `+18666501939` and `+18664159494`)

In Twilio Console, open each toll-free number → `Messaging disabled` → `Resubmit registration`.

### Paste order

1. **Business / Brand Name**
   - `Roadcall.ai (Omniweb, LLC)`

2. **Website URL**
   - `https://roadcall.ai`

3. **Use Case Summary**
   - `Transactional roadside assistance and dispatch notifications for users who request service.`

4. **Message Content Summary**
   - `Roadcall.ai sends service-related messages only: secure location capture links, dispatch status, ETA/tracking, and payment links associated with an active roadside request.`

5. **How End Users Opt In**
   - `Users provide express consent through user-initiated service interactions: inbound roadside calls, web form submission with consent language, or explicit request for SMS updates during AI-assisted dispatch flow.`

6. **How End Users Opt Out**
   - `Every outbound message contains: "Reply STOP to opt out, HELP for help." STOP immediately suppresses further non-essential messages.`

7. **HELP / Support Contact**
   - `support@roadcall.ai`

8. **Policy URLs**
   - SMS Consent: `https://roadcall.ai/sms-consent`
   - Privacy: `https://roadcall.ai/privacy`
   - Terms: `https://roadcall.ai/terms`

9. **Sample Messages** (paste all)
   - `Roadcall.ai: Hi {{first_name}}, tap this secure link to share your location so we can dispatch the nearest mechanic: {{location_link}}. Reply STOP to opt out, HELP for help.`
   - `Roadcall.ai: Dispatch update for request {{request_id}} — we’re contacting nearby providers now. Reply STOP to opt out, HELP for help.`
   - `Roadcall.ai: Your mechanic is on the way. Track ETA here: {{tracking_link}}. Reply STOP to opt out, HELP for help.`
   - `Roadcall.ai: Please authorize payment for roadside service: {{payment_link}}. Reply STOP to opt out, HELP for help.`

10. **Submit**
   - Submit once per toll-free number that shows `Resubmit registration`.

---

## B) A2P 10DLC Campaign Fix (for local `+18134524889`)

In Twilio Console, open `Complete A2P registration` for local number.

### 1) Brand/Business profile checks
- Legal business name matches your official documents.
- EIN and address match exactly.
- Contact email/phone are current.

### 2) Campaign form paste order

1. **Campaign Use Case**
   - Choose closest available in UI: `Low-volume mixed` **or** `Customer Care + Account Notification` (transactional support updates only).

2. **Campaign Description**
   - `Roadcall.ai sends transactional SMS messages related to active roadside assistance requests. Messages include secure location-link delivery, dispatch status updates, ETA/tracking notifications, and payment authorization links requested by the user during a live roadside event. Messages are directly tied to a user-initiated service request.`

3. **Message Flow / Opt-in Description**
   - `Users opt in by initiating service through a roadside call, web request form with SMS consent language, or explicit request for SMS updates during AI-assisted dispatch.`

4. **Opt-in Evidence / URLs**
   - `https://roadcall.ai/sms-consent`
   - `https://roadcall.ai/privacy`
   - `https://roadcall.ai/terms`

5. **Sample Messages** (paste same 4 messages as above)

6. **HELP Message**
   - `Roadcall.ai support: support@roadcall.ai. For immediate assistance call +1 866-650-1939. Msg&data rates may apply. Reply STOP to cancel.`

7. **STOP Message**
   - `You’ve opted out of Roadcall.ai messages. No further messages will be sent. Reply START to re-subscribe.`

8. **Content Category / Marketing Flags**
   - Keep this campaign **transactional** only.
   - Do **not** mix unrelated marketing claims in this campaign.

9. **Submit Campaign**

---

## C) After submit: immediate checks

1. In Twilio numbers page, watch `Traffic Status` for each number.
2. Once enabled, send one internal test SMS to a real mobile (not self-send).
3. Validate app behavior with a real Roadcall location request.

```bash
cd /root/AIRoadcall/backend
./.venv/bin/pytest -q tests/test_retell_dispatch_location.py tests/test_retell_envelope.py
```

4. If one sender still fails, switch to another approved sender in env while review completes.

---

## D) Env toggles to use approved sender quickly

Update `/root/AIRoadcall/.env`:

- `TWILIO_FROM_NUMBER=+1...` (approved sender)
- `TWILIO_MESSAGING_SERVICE_SID=MG...` (recommended once configured)
- `TWILIO_STUDIO_FLOW_SID=FW...` (for Studio path)

Then restart backend so settings reload.
