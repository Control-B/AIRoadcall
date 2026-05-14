# Twilio A2P + Toll-Free Resubmission Fix Pack (Roadcall)

Use this pack to correct common rejection points for:

- **US A2P 10DLC** (local number campaigns)
- **US/CA Toll-Free Verification**

This content is tailored to Roadcall’s roadside dispatch flow.

## 1) What to fix first

1. Ensure every outbound SMS identifies brand and includes opt-out/help language.
2. Use a **single clear use case**: transactional roadside dispatch + status updates.
3. Provide explicit opt-in flow and URLs:
   - `https://roadcall.ai/sms-consent`
   - `https://roadcall.ai/privacy`
   - `https://roadcall.ai/terms`
4. Remove marketing ambiguity unless you are registering a separate marketing campaign.

---

## 2) A2P 10DLC Campaign (copy/paste answers)

### Campaign use case
**Low-volume mixed** or **Customer Care + Account Notification** (choose the closest available in Twilio UI for transactional support updates).

### Campaign description
Roadcall.ai sends transactional SMS messages related to active roadside assistance requests. Messages include secure location-link delivery, dispatch status updates, ETA/tracking notifications, and payment authorization links requested by the user during a live roadside event. Messages are not sold as third-party marketing lists and are directly tied to a user-initiated service request.

### Message flow / Opt-in description
Users opt in by initiating a roadside service request through one of these flows:
1. Calling the Roadcall.ai hotline and requesting roadside dispatch, where SMS follow-up is explicitly requested/expected for link delivery.
2. Submitting a request form on Roadcall.ai and providing a mobile number with SMS consent language.
3. Engaging an AI assistant flow and requesting SMS updates for the active incident.

Consent policy URL: https://roadcall.ai/sms-consent
Privacy policy URL: https://roadcall.ai/privacy
Terms URL: https://roadcall.ai/terms

### Sample messages (paste all)
1. Roadcall.ai: Hi {{first_name}}, tap this secure link to share your location so we can dispatch the nearest mechanic: {{location_link}}. Reply STOP to opt out, HELP for help.
2. Roadcall.ai: Dispatch update for request {{request_id}} — we’re contacting nearby providers now. Reply STOP to opt out, HELP for help.
3. Roadcall.ai: Your mechanic is on the way. Track ETA here: {{tracking_link}}. Reply STOP to opt out, HELP for help.
4. Roadcall.ai: Please authorize payment for roadside service: {{payment_link}}. Reply STOP to opt out, HELP for help.

### HELP response text
Roadcall.ai support: support@roadcall.ai. For immediate assistance call +1 866-415-9494. Msg&data rates may apply. Reply STOP to cancel.

### STOP response text
You’ve opted out of Roadcall.ai messages. No further messages will be sent. Reply START to re-subscribe.

---

## 3) Toll-Free Verification Resubmission (copy/paste answers)

### Use case summary
Transactional roadside assistance and dispatch notifications for users who request service.

### Message content summary
Roadcall.ai sends service-related messages only: secure location capture links, dispatch status, ETA/tracking, and payment links associated with an active roadside request.

### How users opt in
Users provide express consent through user-initiated service interactions:
- inbound roadside calls,
- web form submission with consent language,
- explicit request for SMS updates during AI-assisted dispatch flow.

### How users opt out
Every outbound message contains: “Reply STOP to opt out, HELP for help.”
STOP immediately suppresses further non-essential messages.

### Support contact
support@roadcall.ai

### Website and policy links
- https://roadcall.ai
- https://roadcall.ai/sms-consent
- https://roadcall.ai/privacy
- https://roadcall.ai/terms

---

## 4) Common rejection reasons and exact fixes

- **Missing brand in message** → Start each sample with `Roadcall.ai:`.
- **Missing STOP/HELP language** → Include in every template and sample.
- **Vague use case** → State “transactional roadside dispatch updates tied to active requests.”
- **No clear opt-in proof** → Document call/form/AI-request opt-in path and link consent page.
- **Marketing + transactional mixed** → Keep this campaign strictly transactional; register marketing separately if needed.

---

## 5) Implementation note (already aligned)

Backend SMS templates now include brand + STOP/HELP language by default in `backend/app/services/sms_service.py`.

If you keep Twilio as sender, re-submit using the exact copy above and keep sample messages synchronized with production templates.
