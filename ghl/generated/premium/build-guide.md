# Roadcall Premium - AI Dispatch Snapshot

Plan: Premium ($497/mo + $99 setup)

Roadside providers ready to operationalize AI roadside intake, SMS GPS capture, dispatch workflows, fleet notifications, and emergency call routing.

## Tags
- `roadcall`
- `roadcall:plan-standard`
- `roadcall:new-lead`
- `roadcall:demo-booked`
- `roadcall:customer`
- `roadcall:missed-call`
- `roadcall:ai-receptionist`
- `roadcall:website-widget`
- `roadcall:plan-professional`
- `roadcall:appointment-scheduling`
- `roadcall:review-request`
- `roadcall:multi-location`
- `roadcall:priority-onboarding`
- `roadcall:plan-premium`
- `roadcall:dispatch-event`
- `roadcall:roadside-intake`
- `roadcall:gps-capture`
- `roadcall:fleet-notification`
- `roadcall:emergency-routing`

## Custom Fields
- `roadcall_plan` — Roadcall Plan (single_select)
- `roadcall_organization_id` — Roadcall Organization ID (text)
- `roadcall_lifecycle_event` — Roadcall Lifecycle Event (text)
- `roadcall_lifecycle_event_id` — Roadcall Lifecycle Event ID (text)
- `roadcall_vertical` — Roadcall Vertical (single_select)
- `roadcall_subscription_status` — Roadcall Subscription Status (single_select)
- `roadcall_missed_call_summary` — Roadcall Missed Call Summary (large_text)
- `roadcall_ai_call_summary` — Roadcall AI Call Summary (large_text)
- `roadcall_onboarding_stage` — Roadcall Onboarding Stage (single_select)
- `roadcall_preferred_calendar` — Roadcall Preferred Calendar (text)
- `roadcall_service_area` — Roadcall Service Area (text)
- `roadcall_review_link` — Roadcall Review Link (text)
- `roadcall_last_service_request_id` — Roadcall Last Service Request ID (text)
- `roadcall_last_service_status` — Roadcall Last Service Status (text)
- `roadcall_driver_location` — Roadcall Driver Location (text)
- `roadcall_vehicle_type` — Roadcall Vehicle Type (text)
- `roadcall_problem_type` — Roadcall Problem Type (text)
- `roadcall_fleet_contact` — Roadcall Fleet Contact (text)

## Pipelines
- Roadcall Revenue Pipeline - Standard: New Lead, Contacted, Demo Booked, Checkout Started, Customer Active, At Risk, Churned
- Roadcall Recovery Pipeline - Standard: Missed Call, AI Follow-up Sent, Human Review Needed, Recovered, Lost
- Roadcall Revenue Pipeline - Professional: New Lead, Contacted, Demo Booked, Demo Completed, Checkout Started, Customer Active, Onboarding, Activated, At Risk, Churned
- Roadcall Onboarding Pipeline - Professional: Account Created, Billing Connected, Profile Completed, AI Receptionist Configured, Test Call Completed, Activated
- Roadcall Dispatch Pipeline - Premium: New Roadside Request, Location Requested, Qualified Request, Provider Matched, Transfer In Progress, Successful Transfer, Completed, Needs Follow-up, Cancelled

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
- Roadcall Professional - Demo Booked Confirmation — workflow event: demo_booked
  - Move opportunity to Demo Booked.
  - Send email and SMS confirmation.
  - Send 24-hour and 1-hour reminders.
  - Create follow-up task after demo if subscription_started is missing.
- Roadcall Professional - Customer Onboarding — workflow event: checkout_completed or subscription_started
  - Move opportunity to Customer Active.
  - Create onboarding opportunity.
  - Send kickoff and setup checklist messages.
  - Create internal onboarding task.
  - Escalate incomplete setup after 3 days.
- Roadcall Professional - Review Request — workflow event: completed_job or review_request
  - Wait 2 hours after completed job.
  - Send review SMS and email when consent exists.
  - Send one reminder after 2 days if no review is recorded.
- Roadcall Premium - Roadside Intake Notify — workflow event: qualified_roadside_request
  - Append CRM note with driver city/state, problem type, and vehicle type.
  - Add roadcall:dispatch-event tag.
  - Notify internal ops owner.
  - Do not select providers, quote prices, promise ETA, or change Roadcall service status.
- Roadcall Premium - Successful Transfer Notify — workflow event: successful_transfer
  - Add success note to contact timeline.
  - Move dispatch opportunity to Successful Transfer.
  - Notify fleet contact if configured.
  - Do not handle billing or provider matching in GHL.
- Roadcall Premium - Emergency Escalation — workflow event: missed_call or qualified_roadside_request
  - If urgent roadside keywords are present, create immediate human task.
  - Notify ops owner.
  - Send short acknowledgement SMS when consent exists.
  - Route caller to Roadcall roadside intake or human dispatcher.

## Templates
- Email: Roadcall Standard - Intro — Your Roadcall AI answering setup
- Email: Roadcall Standard - Missed Call Recovery — We saw a missed call
- Email: Roadcall Professional - Onboarding Kickoff — Your Roadcall Professional onboarding
- Email: Roadcall Professional - Review Request — How did Roadcall do?
- Email: Roadcall Premium - Dispatch Milestone — Roadcall dispatch update
- SMS: Roadcall Standard - New Lead SMS
- SMS: Roadcall Standard - Missed Call SMS
- SMS: Roadcall Professional - Demo Reminder
- SMS: Roadcall Professional - Review SMS
- SMS: Roadcall Premium - Location Link
- SMS: Roadcall Premium - Fleet Notify

## Snapshot Step
Build or apply these assets to a clean source sub-account, verify the checklist, then save that source sub-account as an official GHL Snapshot from the agency UI.
