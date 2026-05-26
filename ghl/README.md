# Roadcall GHL Operating Kit

This directory contains the GHL-side implementation blueprint for Roadcall onboarding, email/SMS marketing, missed-call recovery, and AI telephony.

Roadcall remains the source of truth for operations. GHL should react to lifecycle events from Roadcall and handle CRM/automation only.

## Files

- `ghl/roadcall-ghl-setup.json` — structured setup blueprint for fields, tags, pipelines, workflows, templates, AI receptionist guardrails, Ask AI prompts, and acceptance tests.
- `ghl/roadcall-plan-snapshots.json` — plan-specific blueprint definitions for the Standard, Professional, and Premium GHL snapshot builds.
- `backend/scripts/build_ghl_plan_snapshots.py` — dry-run-first generator that writes per-plan build artifacts and can optionally apply supported LeadConnector assets to a location.
- `docs/ghl-safe-crm-sync.md` — the allow/deny list for syncing CRM-safe mechanic, shop, and vendor contact data to GHL without exporting the private provider database.

## Plan Snapshot Builder

GHL's official agency snapshot is best treated as the final saved copy of a configured source sub-account. Build the plan assets into a clean source location, verify them, then save that location as the official GHL Snapshot in the agency UI.

Generate all three plan build packages without touching GHL:

```bash
python backend/scripts/build_ghl_plan_snapshots.py
```

Generate one package:

```bash
python backend/scripts/build_ghl_plan_snapshots.py --plan professional
```

Apply supported location assets only after setting secrets in your shell. The script does not print the API key.

```bash
export GHL_API_KEY="REPLACE_WITH_GHL_KEY"
export GHL_LOCATION_ID="REPLACE_WITH_SOURCE_LOCATION_ID"
python backend/scripts/build_ghl_plan_snapshots.py --plan standard --apply
```

The apply mode is intentionally conservative. It creates supported tags and custom fields, then leaves pipelines, workflows, templates, AI prompts, calendars, and final snapshot saving for the generated build guide / GHL UI because those surfaces vary by account/API capability.

## Implementation Order

1. Create the custom fields from `customFields`.
2. Create the tags from `tags`.
3. Create the three pipelines from `pipelines`.
4. Use each `askAiPrompts` entry in GHL Ask AI to draft workflows and the AI receptionist script.
5. Build each `workflowBlueprints` workflow manually or refine the Ask AI draft.
6. Add the `emailTemplates` and `smsTemplates` copy.
7. Connect Roadcall events through the GHL integration page in Roadcall admin.
8. Test every item in `acceptanceTests` before turning workflows on.

For pricing-plan snapshots, repeat the same order against each generated source-location guide under `ghl/generated/<plan>/`.

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

For field-level sync rules, use `docs/ghl-safe-crm-sync.md` as the source of truth. GHL should receive selected CRM-safe contact records for marketing and onboarding, not the full mechanics or national vendors database.
