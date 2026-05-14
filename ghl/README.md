# Roadcall GHL Operating Kit

This directory contains the GHL-side implementation blueprint for Roadcall onboarding, email/SMS marketing, missed-call recovery, and AI telephony.

Roadcall remains the source of truth for operations. GHL should react to lifecycle events from Roadcall and handle CRM/automation only.

## Files

- `ghl/roadcall-ghl-setup.json` — structured setup blueprint for fields, tags, pipelines, workflows, templates, AI receptionist guardrails, Ask AI prompts, and acceptance tests.

## Implementation Order

1. Create the custom fields from `customFields`.
2. Create the tags from `tags`.
3. Create the three pipelines from `pipelines`.
4. Use each `askAiPrompts` entry in GHL Ask AI to draft workflows and the AI receptionist script.
5. Build each `workflowBlueprints` workflow manually or refine the Ask AI draft.
6. Add the `emailTemplates` and `smsTemplates` copy.
7. Connect Roadcall events through the GHL integration page in Roadcall admin.
8. Test every item in `acceptanceTests` before turning workflows on.

## Required Roadcall Events

The backend emits these lifecycle events through `LifecycleService`:

- `new_lead`
- `demo_booked`
- `subscription_started`
- `subscription_updated`
- `subscription_cancelled`
- `checkout_completed`
- `invoice_paid`
- `payment_failed`
- `qualified_roadside_request`
- `successful_transfer`
- `completed_job`
- `review_request`
- `missed_call`
- `contact_updated`

## Do Not Move Into GHL

Do not make GHL responsible for:

- dispatch matching
- mechanic/vendor selection
- transfer billing
- Stripe subscription truth
- service status truth
- fleet account state
- national vendor data
- marketplace analytics

GHL can display notes, tags, tasks, and opportunities based on Roadcall events, but Roadcall owns the operational record.
