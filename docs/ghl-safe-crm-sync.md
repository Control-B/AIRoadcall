# GHL Safe CRM Sync List

This guide defines what Roadcall can safely send from the mechanics, shops, and vendor data into GoHighLevel without making GHL the system of record for the private provider marketplace.

## Rule

Roadcall keeps the full mechanics and national vendors database. GHL receives only CRM-safe contact, campaign, and sales pipeline data for records selected for marketing, sales, onboarding, or customer follow-up.

Do not bulk export the whole provider database to GHL. Sync only eligible records, and only with the fields listed below.

## Physical GHL List

Use `ghl/safe-crm-import-template.csv` as the physical list format for GHL imports or contact sync jobs.

You do not upload the full database to GHL. You select eligible records from Roadcall, copy only the safe columns into this CSV format, then import or sync that selected list to GHL.

In the Roadcall admin dashboard, use **Admin > Mechanic Database > GHL Safe List** to generate this same safe duplicate from the current database filters. That dashboard export uses the backend `/api/mechanics/admin/ghl-safe-list` endpoint and excludes private operational fields by design.

The template columns are:

```csv
business_name,contact_name,phone,email,website,public_address,city,state,business_category,lead_source,marketing_segment,plan_interest,pipeline_stage,onboarding_stage,sms_consent,email_consent,consent_source,consent_timestamp,roadcall_public_reference_id,tags,notes
```

Use this file for campaigns such as:

- AI telephony shop outreach.
- Widget or website upsell.
- Standard, Professional, or Advanced plan sales.
- Customer onboarding.
- Missed-call or review follow-up.

Do not add columns for exact coordinates, scores, source URLs, dispatch data, service radius, private notes, or provider matching metadata.

## Sync To GHL

These fields are safe for GHL contacts, opportunities, tags, campaigns, and workflows:

| Data | GHL use |
| --- | --- |
| Business name | Contact/company display name. |
| Owner or manager name | Sales and onboarding personalization. |
| Business phone | Calling and SMS campaigns when consent/compliance allows. |
| Business email | Email campaigns and onboarding. |
| Website | Sales research and contact profile. |
| Public address or city/state | Territory segmentation and local campaign copy. |
| Public business category | Segments such as diesel shop, mobile mechanic, towing, tire, trailer repair, dealership, national vendor contact. |
| Lead source | Examples: Roadcall directory, inbound form, admin import, referral, event, outbound campaign. |
| Marketing segment | Examples: AI telephony interest, widget interest, Professional plan interest, Advanced website interest. |
| Plan interest | Standard, Professional, Advanced, AI Telephony Only, Widget Only, Widget + AI Telephony. |
| Sales pipeline stage | New Lead, Contacted, Demo Booked, Checkout Started, Customer Active, Onboarding, Activated, Lost. |
| Onboarding stage | Profile completed, phone connected, calendar connected, AI configured, test call completed, activated. |
| Campaign tags | `roadcall:*` tags used to start or stop GHL workflows. |
| Consent status | SMS/email eligibility, opt-out state, consent source, consent timestamp. |
| Public Roadcall reference ID | A non-sensitive ID used to link GHL back to Roadcall. |
| Last CRM sync timestamp | Operational visibility for admins. |
| AI call summary | Sales/support summary only; do not include private dispatch data or exact caller GPS. |
| Missed call summary | Recovery workflow context. |
| Review link | Reputation campaigns. |
| Demo or appointment metadata | Confirmation/reminder workflows. |

## Keep In Roadcall Only

These fields must not be synced to GHL as CRM fields, campaign data, workflow state, or exported lists:

| Data | Reason |
| --- | --- |
| Full mechanics database | Roadcall is the marketplace source of truth. |
| Full national vendor database | Roadcall owns vendor search and routing logic. |
| Exact latitude/longitude | Used for dispatch and matching, not marketing. |
| Service radius | Part of provider matching logic. |
| Internal provider score or rank | Proprietary matching signal. |
| Dispatch priority | Operational decisioning belongs in Roadcall. |
| Private source URLs | Internal enrichment/source metadata. |
| Raw enrichment payloads | Not needed for CRM and may contain noisy/private data. |
| Internal notes used for matching | Operational/private context. |
| Mechanic offer state | Lead marketplace and payment gate state belong in Roadcall. |
| Lead fee/payment unlock state | Roadcall/Stripe operational state. |
| Caller GPS or exact breakdown location | Sensitive live dispatch data. |
| Dispatch session history | Roadcall operational record. |
| Provider accept/reject history | Marketplace performance and dispatch intelligence. |
| Fleet account operational data | Fleet operations stay in Roadcall. |
| Vendor routing rules | Proprietary operational logic. |
| API keys, webhook secrets, tokens | Secrets stay encrypted in Roadcall/env stores. |

## Eligibility Rules

A mechanic, shop, or vendor record can sync to GHL only when at least one condition is true:

- A human admin selected it for outreach.
- The business submitted a Roadcall or GHL form.
- The business booked a demo or setup appointment.
- The business opted into SMS or email communication.
- The business is an existing Roadcall customer.
- The business is part of a specific approved campaign segment.
- The record has enough public contact data for compliant sales outreach.

Do not sync records only because they exist in the provider directory.

## Recommended GHL Tags

Use tags to control campaign entry, segmentation, and suppression:

- `roadcall`
- `roadcall:shop`
- `roadcall:vendor`
- `roadcall:national-vendor-contact`
- `roadcall:prospect`
- `roadcall:customer`
- `roadcall:standard-interest`
- `roadcall:professional-interest`
- `roadcall:advanced-interest`
- `roadcall:ai-telephony-interest`
- `roadcall:widget-interest`
- `roadcall:demo-booked`
- `roadcall:onboarding`
- `roadcall:activated`
- `roadcall:a2p-consented`
- `roadcall:email-consented`
- `roadcall:cold-outreach`
- `roadcall:do-not-market`
- `roadcall:do-not-sync`

## Recommended Custom Fields

Create these GHL custom fields for safe CRM sync:

| Field | Key | Type |
| --- | --- | --- |
| Roadcall Public Reference ID | `roadcall_public_reference_id` | Text |
| Roadcall Organization ID | `roadcall_organization_id` | Text |
| Roadcall Vertical | `roadcall_vertical` | Single select: shop, vendor, fleet, driver, general |
| Roadcall Plan Interest | `roadcall_plan_interest` | Single select: standard, professional, advanced, ai_telephony, widget_only, widget_voice |
| Roadcall Marketing Segment | `roadcall_marketing_segment` | Text |
| Roadcall Lead Source | `roadcall_lead_source` | Text |
| Roadcall City | `roadcall_city` | Text |
| Roadcall State | `roadcall_state` | Text |
| Roadcall Business Category | `roadcall_business_category` | Text |
| Roadcall CRM Sync Status | `roadcall_crm_sync_status` | Single select: eligible, synced, failed, do_not_sync, opted_out |
| Roadcall SMS Consent | `roadcall_sms_consent` | Checkbox |
| Roadcall Email Consent | `roadcall_email_consent` | Checkbox |
| Roadcall Consent Source | `roadcall_consent_source` | Text |
| Roadcall Last CRM Sync At | `roadcall_last_crm_sync_at` | Date/time |
| Roadcall AI Call Summary | `roadcall_ai_call_summary` | Large text |
| Roadcall Missed Call Summary | `roadcall_missed_call_summary` | Large text |

## Example Safe Payload

```json
{
  "entity_type": "mechanic_prospect",
  "entity_id": "mechanic_12345",
  "name": "ABC Diesel Repair",
  "company": "ABC Diesel Repair",
  "email": "owner@example.com",
  "phone": "+15555555555",
  "source": "roadcall_provider_directory",
  "tags": [
    "roadcall",
    "roadcall:shop",
    "roadcall:prospect",
    "roadcall:ai-telephony-interest"
  ],
  "custom_fields": [
    {"key": "roadcall_public_reference_id", "value": "provider_public_abc123"},
    {"key": "roadcall_vertical", "value": "shop"},
    {"key": "roadcall_plan_interest", "value": "professional"},
    {"key": "roadcall_city", "value": "Tallahassee"},
    {"key": "roadcall_state", "value": "FL"},
    {"key": "roadcall_lead_source", "value": "provider_directory"},
    {"key": "roadcall_crm_sync_status", "value": "eligible"}
  ]
}
```

## Sync Flow

1. Admin or campaign rule selects eligible records in Roadcall.
2. Roadcall filters out `do_not_sync`, `do_not_market`, opted-out, and incomplete records.
3. Roadcall builds a CRM-safe payload using only the allowed fields.
4. Roadcall sends the payload to GHL contact sync.
5. GHL applies tags, custom fields, opportunities, and workflows.
6. GHL sends campaign messages through the approved A2P number.
7. GHL webhooks send form, appointment, contact, and call-summary events back to Roadcall.
8. Roadcall records sync status and keeps operational provider data private.

## Compliance Notes

- A2P approval does not make every phone number eligible for SMS marketing.
- Keep SMS consent, opt-out, and suppression state synchronized.
- Use GHL for SMS delivery because the approved A2P number lives there.
- Keep Roadcall as the system that decides which records are eligible for campaign sync.
- Every marketing SMS should include opt-out language where required, such as `Reply STOP to opt out`.