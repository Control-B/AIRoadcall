# Roadcall 48-Hour Market-Ready Checklist

This checklist focuses on fixes we can execute immediately in code/infrastructure, while separating tasks that belong in GoHighLevel.

## Ownership legend

- **Repo**: changes in this repository or hosting/runtime config.
- **GHL**: GoHighLevel workflows/pipelines/campaigns.
- **Shared**: integration and validation across both.

## 0-6 hours: Stability and critical UX

- [ ] **Repo**: Confirm homepage and core routes load without client exceptions (`/`, `/pricing`, `/shops/onboarding`, `/demo`, `/search`, `/admin/login`).
- [ ] **Repo**: Verify fallback UI for route and global render errors (Next.js `error.tsx` + `global-error.tsx`).
- [ ] **Repo**: Validate API health endpoint and core dispatch/mechanic lookup endpoints.
- [ ] **Shared**: Submit one test lead from homepage and verify it reaches backend and downstream automation.

**Done definition**
- No P0/P1 user-facing breakages on key routes.
- All critical pages return 2xx and render interactive CTAs.

## 6-12 hours: Security and abuse controls

- [ ] **Repo**: Re-verify Redis stays internal-only (no public `6379`).
- [ ] **Repo**: Confirm admin and sensitive data endpoints reject unauthenticated access.
- [ ] **Repo**: Validate rate limits on public write surfaces (`/api/leads`, marketplace submissions/reviews).
- [ ] **Shared**: Ensure webhook endpoints validate shared secret/token and reject invalid signatures.

**Done definition**
- External scan finds no exposed data services.
- Unauthorized requests are consistently denied with correct status codes.

## 12-24 hours: Revenue path and conversion flow

- [ ] **Repo**: Test CTA path integrity (`/pricing` -> `/shops/onboarding` -> submit success path).
- [ ] **Repo**: Verify copy and pricing consistency across homepage, pricing, and onboarding pages.
- [ ] **GHL**: Confirm pipeline stages are correct for new leads (new, contacted, qualified, booked, won/lost).
- [ ] **GHL**: Confirm missed-call text-back and demo follow-up workflows are active.
- [ ] **Shared**: Validate lead field mapping (name, phone, email, vertical, source) end-to-end.

**Done definition**
- 100% of test leads appear in the intended stage with complete field mapping.

## 24-36 hours: Operational readiness

- [ ] **Repo**: Run smoke script before/after any deploy and archive output.
- [ ] **Repo**: Confirm deploy rollback path to last known good image/revision.
- [ ] **GHL**: Confirm ownership routing and SLA notifications for new leads.
- [ ] **Shared**: Run one incident drill (failed onboarding submission + missed-call event).

**Done definition**
- Team can detect and triage production incidents within 15 minutes.

## 36-48 hours: Launch gate

- [ ] **Repo**: Verify uptime probes and error alerting are active.
- [ ] **Repo**: Validate no regressions on public routes after latest deploy.
- [ ] **GHL**: Verify all launch workflows are enabled and not in draft mode.
- [ ] **Shared**: Final go/no-go review with evidence links for each checklist item.

**Done definition**
- All checklist items either complete or explicitly accepted as deferred with owner/date.

## Evidence template

For each item, attach:

- Owner
- Timestamp
- Environment (`prod`/`staging`)
- Proof (screenshot, curl output, dashboard link)
- Result (`pass`/`fail`/`deferred`)
