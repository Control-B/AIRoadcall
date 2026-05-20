# Roadcall Standard - AI Telephony Snapshot

Plan: Standard ($299/mo + $99 setup)

Small mechanics and mobile roadside businesses that need AI telephony, leads, calendar, CRM, form builder, and missed-call text back.

## Tags
- `roadcall`
- `roadcall:plan-standard`
- `roadcall:new-lead`
- `roadcall:demo-booked`
- `roadcall:customer`
- `roadcall:missed-call`
- `roadcall:ai-receptionist`
- `roadcall:website-widget`

## Custom Fields
- `roadcall_plan` — Roadcall Plan (single_select)
- `roadcall_organization_id` — Roadcall Organization ID (text)
- `roadcall_lifecycle_event` — Roadcall Lifecycle Event (text)
- `roadcall_lifecycle_event_id` — Roadcall Lifecycle Event ID (text)
- `roadcall_vertical` — Roadcall Vertical (single_select)
- `roadcall_subscription_status` — Roadcall Subscription Status (single_select)
- `roadcall_missed_call_summary` — Roadcall Missed Call Summary (large_text)
- `roadcall_ai_call_summary` — Roadcall AI Call Summary (large_text)

## Pipelines
- Roadcall Revenue Pipeline - Standard: New Lead, Contacted, Demo Booked, Checkout Started, Customer Active, At Risk, Churned
- Roadcall Recovery Pipeline - Standard: Missed Call, AI Follow-up Sent, Human Review Needed, Recovered, Lost

## Workflows
- Roadcall Standard - New Lead Speed to Lead — workflow event: new_lead
  - Create or update contact with roadcall and roadcall:plan-standard tags.
  - Create an opportunity in Roadcall Revenue Pipeline - Standard at New Lead.
  - Send immediate intro SMS and email with demo CTA.
  - Create a sales task if no demo is booked after 15 minutes.
  - Stop when demo_booked, checkout_completed, or subscription_started arrives.
- Roadcall Standard - Missed Call Recovery — workflow event: missed_call
  - Add roadcall:missed-call and roadcall:ai-receptionist tags.
  - Create recovery opportunity at Missed Call.
  - Send short recovery SMS with opt-out language.
  - Create urgent task due in 5 minutes.
  - Move to Recovered only after human or Roadcall confirmation.

## Templates
- Email: Roadcall Standard - Intro — Your Roadcall AI telephony setup
- Email: Roadcall Standard - Missed Call Recovery — We saw a missed call
- SMS: Roadcall Standard - New Lead SMS
- SMS: Roadcall Standard - Missed Call SMS

## Snapshot Step
Build or apply these assets to a clean source sub-account, verify the checklist, then save that source sub-account as an official GHL Snapshot from the agency UI.
