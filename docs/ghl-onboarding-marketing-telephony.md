# GHL Build Guide: Onboarding, Email Marketing, and AI Telephony

This guide explains how to build the GHL side of Roadcall using the lifecycle event bus in Roadcall and the setup kit in `ghl/roadcall-ghl-setup.json`.

## Operating Principle

Roadcall owns product and operational truth. GHL owns sales, marketing, reminders, missed-call recovery, and AI receptionist follow-up.

Use this boundary:

- Roadcall emits lifecycle events.
- GHL reacts with workflows, tasks, tags, opportunities, emails, SMS, and AI call summaries.
- Stripe owns billing truth.
- GHL should never dispatch mechanics, choose providers, authorize charges, or decide service status.

## 1. Create Custom Fields

Create these fields in GHL before workflows are activated:

| Field | Key | Purpose |
| --- | --- | --- |
| Roadcall Organization ID | `roadcall_organization_id` | Links GHL contact/account to Roadcall tenant. |
| Roadcall Lifecycle Event | `roadcall_lifecycle_event` | Last Roadcall event received. |
| Roadcall Lifecycle Event ID | `roadcall_lifecycle_event_id` | Audit link to Roadcall lifecycle event. |
| Roadcall Vertical | `roadcall_vertical` | Fleet, shop, vendor, or general. |
| Roadcall Subscription Status | `roadcall_subscription_status` | CRM display of billing lifecycle; Stripe/Roadcall remain authoritative. |
| Roadcall Onboarding Stage | `roadcall_onboarding_stage` | CRM display of onboarding progress. |
| Roadcall Last Service Request ID | `roadcall_last_service_request_id` | Last visible service request reference. |
| Roadcall Last Service Status | `roadcall_last_service_status` | CRM display only. |
| Roadcall Missed Call Summary | `roadcall_missed_call_summary` | Missed-call recovery context. |
| Roadcall AI Call Summary | `roadcall_ai_call_summary` | AI receptionist summary. |

## 2. Create Tags

Create the tags listed in `ghl/roadcall-ghl-setup.json`. Use `roadcall:*` naming so Roadcall automation stays isolated from unrelated GHL automations.

Recommended required tags:

- `roadcall`
- `roadcall:new-lead`
- `roadcall:demo-booked`
- `roadcall:customer`
- `roadcall:missed-call`
- `roadcall:dispatch-event`
- `roadcall:review-request`
- `roadcall:past-due`
- `roadcall:ai-receptionist`

## 3. Create Pipelines

Create three GHL pipelines:

### Roadcall Revenue Pipeline

Stages:

1. New Lead
2. Contacted
3. Demo Booked
4. Demo Completed
5. Checkout Started
6. Customer Active
7. Onboarding
8. Activated
9. At Risk
10. Churned

### Roadcall Onboarding Pipeline

Stages:

1. Account Created
2. Billing Connected
3. Profile Completed
4. AI Receptionist Configured
5. Test Call Completed
6. First Dispatch Completed
7. Activated

### Roadcall Recovery Pipeline

Stages:

1. Missed Call
2. AI Follow-up Sent
3. Human Review Needed
4. Recovered
5. Lost

## 4. Use Ask AI to Draft Workflows

Paste the prompts from `askAiPrompts` in `ghl/roadcall-ghl-setup.json` into GHL Ask AI.

After Ask AI generates each workflow, manually verify:

- trigger event name matches the Roadcall event exactly
- tags use `roadcall:*`
- pipeline/stage names match this guide
- stop conditions are present
- SMS actions include opt-out compliance language
- billing links route to Stripe billing portal
- dispatch/service messages do not promise ETA, provider availability, or final repair price

## 5. Build Core Workflows

### New Lead Speed to Lead

Trigger: `new_lead`

Actions:

1. Create/update contact.
2. Add tags `roadcall` and `roadcall:new-lead`.
3. Apply vertical tag if available.
4. Create opportunity in Roadcall Revenue Pipeline at New Lead.
5. Send immediate intro email.
6. Send SMS if phone exists and consent allows.
7. Create sales task if no demo is booked within 15 minutes.
8. Send value email after 1 day.
9. Send case-study email after 3 days.
10. Stop if `demo_booked`, `checkout_completed`, or `subscription_started` arrives.

### Demo Booked Confirmation

Trigger: `demo_booked`

Actions:

1. Move opportunity to Demo Booked.
2. Add tag `roadcall:demo-booked`.
3. Send confirmation email.
4. Send confirmation SMS.
5. Send reminders 24 hours and 1 hour before demo.
6. Create follow-up task after demo if no subscription event arrives.

### Customer Onboarding

Trigger: `subscription_started` or `checkout_completed`

Actions:

1. Move opportunity to Customer Active.
2. Add tags `roadcall:customer` and applicable subscription status tag.
3. Create onboarding opportunity at Account Created.
4. Send onboarding kickoff email.
5. Send setup checklist email.
6. Create same-day onboarding task.
7. Remind after 1 day if not activated.
8. Escalate after 3 days if incomplete.
9. Stop when Roadcall reports first test call, first dispatch, or activation.

### Missed Call Recovery

Trigger: `missed_call`

Actions:

1. Add tags `roadcall:missed-call` and `roadcall:ai-receptionist`.
2. Create recovery opportunity at Missed Call.
3. Send recovery SMS if consent exists.
4. Send email with AI call summary if email exists.
5. Create urgent task due in 5 minutes.
6. Notify owner/manager if unresolved after 15 minutes.
7. Move to Recovered only after human confirmation or Roadcall recovery event.

### Dispatch Milestone Notify

Triggers: `qualified_roadside_request`, `successful_transfer`, `completed_job`

Actions:

1. Append CRM note.
2. Add tag `roadcall:dispatch-event`.
3. Notify internal ops if needed.
4. Do not change provider matching, service status, billing, or ETA.
5. For `completed_job`, trigger review workflow after a short delay.

### Failed Payment Save

Trigger: `payment_failed`

Actions:

1. Move opportunity to At Risk.
2. Add tag `roadcall:past-due`.
3. Send billing update email with Stripe billing portal link.
4. Send SMS if consent exists.
5. Create finance/support task.
6. Stop when `invoice_paid` or `subscription_updated` arrives.

## 6. Build AI Receptionist

Use GHL AI for:

- demo booking
- missed-call recovery
- onboarding help
- basic lead qualification
- call summaries
- routing urgent operational calls to Roadcall or a human

Do not use GHL AI for:

- selecting mechanics
- quoting exact repair costs
- promising ETA
- charging cards
- changing Roadcall service status
- resolving live dispatch decisions

### AI Receptionist Prompt

Use the `aiReceptionist` section in `ghl/roadcall-ghl-setup.json` as the source prompt.

Minimum guardrails:

- disclose call recording if configured and legally required
- escalate active roadside emergencies
- do not promise mechanic availability
- do not quote final costs
- do not collect full payment card details
- summarize every call in the expected format

## 7. Connect GHL to Roadcall

In Roadcall admin, use the GHL Integration page to configure:

- Roadcall organization ID
- GHL location ID
- subaccount name
- encrypted access token
- encrypted refresh token if used
- webhook secret
- pipeline ID
- default workflow ID if applicable

### API-key onboarding shortcut (new)

If you want Roadcall to help create/verify the GHL subaccount and save tenant mapping in one call, use:

- `POST /api/ghl/admin/onboarding/setup`
- Header: `x-admin-key: <ADMIN_API_KEY>`

Environment variables used by this flow:

- `GHL_API_KEY` (agency or location API key)
- `GHL_LOCATION_ID` (optional default location)
- `GHL_FROM_NUMBER` (optional, for GHL SMS sender override)

Example (create subaccount + map tenant):

```bash
curl -X POST "$API_BASE/api/ghl/admin/onboarding/setup" \
  -H "x-admin-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{
    "organization_id": "REPLACE_WITH_ORG_UUID",
    "create_subaccount": true,
    "subaccount_name": "Roadcall Fleet - Test",
    "subaccount_payload": {
      "name": "Roadcall Fleet - Test",
      "companyName": "Roadcall Fleet"
    },
    "pipeline_id": "OPTIONAL_PIPELINE_ID",
    "default_workflow_id": "OPTIONAL_WORKFLOW_ID"
  }'
```

Example (existing location only):

```bash
curl -X POST "$API_BASE/api/ghl/admin/onboarding/setup" \
  -H "x-admin-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{
    "organization_id": "REPLACE_WITH_ORG_UUID",
    "location_id": "REPLACE_WITH_LOCATION_ID",
    "subaccount_name": "Roadcall Fleet - Existing",
    "pipeline_id": "OPTIONAL_PIPELINE_ID",
    "default_workflow_id": "OPTIONAL_WORKFLOW_ID"
  }'
```

If Twilio traffic is blocked, Roadcall can temporarily use GHL SMS for location-link delivery when `GHL_API_KEY` + `GHL_LOCATION_ID` are set.

Roadcall endpoints already exist for:

- outbound lead/contact/workflow sync
- signed inbound GHL forms
- signed inbound contact updates
- signed inbound appointments
- signed inbound voice-call summaries
- retry queue processing
- lifecycle event list/create/retry

## 7.1 Build Plan-Specific Snapshot Blueprints

The three current Roadcall shop plans are:

- Standard — $299/mo + $99 setup: AI Telephony, Leads, Calendar, CRM, Form Builder, and Missed Call Text Back.
- Professional — $499/mo + $199 setup: everything in Standard plus Website, Web Chat, Email Marketing, and Survey Builder.
- Advanced — $999/mo + $299 setup: everything in Professional plus Social Media Marketing, Funnels, and deeper Email Marketing automation.

Use the snapshot builder to generate source-location build guides:

```bash
python backend/scripts/build_ghl_plan_snapshots.py
```

Artifacts are written to:

- `ghl/generated/standard/`
- `ghl/generated/premium/`
- `ghl/generated/advanced/`

If you want the script to push the safe subset of assets to a clean GHL source location, set `GHL_API_KEY` and `GHL_LOCATION_ID`, then run:

```bash
python backend/scripts/build_ghl_plan_snapshots.py --plan advanced --apply
```

The script does not print secrets. It applies only conservative, location-level assets currently represented as tags and custom fields. After that, use the generated guide to create/verify pipelines, workflows, templates, calendars, and AI prompts, then save the configured source location as the official GHL agency Snapshot.

## 8. Acceptance Test Checklist

Before turning workflows on, confirm:

- `new_lead` creates/updates contact, creates opportunity, sends intro email/SMS.
- `demo_booked` moves the opportunity and schedules reminders.
- `checkout_completed` starts onboarding but does not mutate Stripe directly.
- `subscription_started` moves customer into active onboarding.
- `payment_failed` sends Stripe billing portal CTA and creates support task.
- `missed_call` sends recovery message and creates urgent task.
- dispatch milestone events create notes only and do not control operations.
- AI receptionist call summary lands in the expected custom field.
- opt-out language appears on SMS messages.
- no workflow exposes mechanic database, vendor source URLs, internal IDs, or operational secrets.

## 9. Useful Test Commands

After configuring GHL tenant mapping in Roadcall, use Roadcall lifecycle endpoints to test workflow triggers with an admin token.

```bash
curl -X POST "$API_BASE/api/lifecycle/events" \
  -H "x-admin-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{
    "event_type": "new_lead",
    "source": "manual_test",
    "organization_id": "REPLACE_WITH_ORG_ID",
    "entity_type": "lead",
    "entity_id": "manual-test-lead",
    "payload": {
      "email": "test@example.com",
      "name": "Test Lead",
      "vertical": "fleet"
    },
    "idempotency_key": "manual-test-new-lead-001"
  }'
```

```bash
curl "$API_BASE/api/lifecycle/events?limit=10" \
  -H "x-admin-key: $ADMIN_API_KEY"
```

```bash
curl -X POST "$API_BASE/api/ghl/retry/process" \
  -H "x-admin-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"limit": 25}'
```

## 10. Launch Recommendation

Launch in this order:

1. New Lead Speed to Lead
2. Demo Booked Confirmation
3. Customer Onboarding
4. Missed Call Recovery
5. Failed Payment Save
6. Dispatch Milestone Notify
7. Review Request

Keep all workflows in draft until the acceptance checklist passes with a test GHL subaccount.
