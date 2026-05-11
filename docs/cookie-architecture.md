# Roadcall.ai cookie & session architecture

This document describes every cookie and storage key Roadcall.ai sets, **why**
it exists, and how it stays compliant. The implementation lives in:

| Layer    | File                                       |
| -------- | ------------------------------------------ |
| Backend  | `backend/app/core/cookies.py`              |
| Backend  | `backend/app/core/session_middleware.py`   |
| Backend  | `backend/app/api/routes/admin_auth.py`     |
| Frontend | `frontend/src/lib/cookies.ts`              |
| Frontend | `frontend/src/lib/consent.ts`              |
| Frontend | `frontend/src/lib/language.ts`             |
| Frontend | `frontend/src/lib/sessions.ts`             |
| Frontend | `frontend/src/lib/ui-prefs.ts`             |
| Frontend | `frontend/src/components/CookieConsent.tsx`|
| Frontend | `frontend/src/middleware.ts`               |

## Principles

1. **Essential cookies only by default.** Analytics/marketing scripts do not
   load until the user explicitly consents.
2. **Opaque random IDs, never PII.** Cookies hold reference IDs only. All real
   data (GPS, payment, transcripts, mechanic assignments) lives in Postgres.
3. **HttpOnly for anything that grants access.** Auth, refresh, roadside,
   location, and the anonymous correlation cookie are HttpOnly so JS can never
   read them.
4. **`Secure` outside localhost.** Set automatically based on
   `APP_BASE_URL`/`FRONTEND_URL`.
5. **`SameSite=Lax`** for every cookie. We do not use cross-site embedding.
6. **Path-scoped** where it helps (`/api/admin` for refresh, `/locate` for the
   GPS capture cookie).
7. **Fallback when cookies are blocked**: every operational flow validates a
   server-side token (URL token for SMS GPS links, header token for admin
   APIs) so Safari private mode and aggressive cookie blockers still work.

## Cookies

| Name | Purpose | TTL | HttpOnly | Path |
| ---- | ------- | --- | -------- | ---- |
| `roadcall_auth_session`        | Logged-in dashboard session token | 24h  | ✅ | `/` |
| `roadcall_refresh_session`     | Long-lived refresh token          | 30d  | ✅ | `/api/admin` |
| `roadcall_client_session_id`   | Anonymous correlation / abuse-control ID | 30d | ✅ | `/` |
| `roadcall_roadside_session_id` | In-flight roadside request reference | 6h   | ✅ | `/` |
| `roadcall_location_session_id` | SMS GPS capture session reference | 60m  | ✅ | `/locate` |
| `roadcall_ai_conversation_id`  | AI chat continuity reference      | 24h  | ❌ | `/` |
| `roadcall_preferred_language`  | UI language (BCP-47)              | 180d | ❌ | `/` |
| `roadcall_cookie_consent`      | "User answered the banner"        | 365d | ❌ | `/` |
| `roadcall_analytics_consent`   | `granted` / `denied`              | 365d | ❌ | `/` |

### Never stored in cookies

GPS coordinates, payment details, full names, phone numbers, email addresses,
truck/vehicle details, mechanic assignments, AI transcript content, API keys,
JWT secrets, tenant config. All of these stay in the backend database.

## localStorage (UI only)

| Key | Purpose |
| --- | ------- |
| `roadcall.ui.theme`                | `light` \| `dark` \| `default` |
| `roadcall.ui.sidebar_collapsed`    | dashboard sidebar state |
| `roadcall.ui.last_view`            | last selected dashboard view |
| `roadcall.ui.notifications`        | enable/disable in-app notifications |

Nothing business-critical is stored client-side.

## Request correlation

The backend `SessionCorrelationMiddleware` runs on every request and:

- Auto-creates `roadcall_client_session_id` if missing.
- Reads every `roadcall_*` cookie and stashes them on `request.state` for any
  handler / log line.
- Echoes `X-Roadcall-Request` (per-request UUID) and `X-Roadcall-Client`
  (the anonymous ID) response headers for browser dev-tools debugging.
- Logs structured `request_complete` events with truncated session refs so
  ops can correlate a customer-reported issue across:
  `client_session_id` → `roadside_session_id` → `job_id`
  → `ai_conversation_id` → `user_id`.

Webhook and `/health` paths are skipped to keep the hot path cheap.

## Consent banner

`<CookieConsent />` is mounted in `app/layout.tsx`. On first visit:

1. Banner renders bottom-of-screen with the required notice text.
2. User picks **Accept all** / **Reject optional** / **Preferences**.
3. Choice is stored in `roadcall_cookie_consent` (=`1`) and
   `roadcall_analytics_consent` (=`granted`/`denied`).
4. Analytics loaders should call `isAnalyticsAllowed()` before injecting any
   third-party script. They should also subscribe to the
   `roadcall:consent` window event so revoking takes effect immediately.

To re-open the banner from a footer link:

```ts
window.dispatchEvent(new CustomEvent("roadcall:open-consent"));
```

## Operational flows tested

- First-visit cookie issuance (anonymous correlation).
- Roadside flow continuity (issue → location → vehicle → payment → assignment
  → tracking) using the same `roadcall_roadside_session_id`.
- SMS GPS link with URL-token fallback when cookies are blocked.
- AI chat session reuse on refresh — no duplicate welcome message because the
  `roadcall_ai_conversation_id` is read first and reused.
- Admin login: HttpOnly cookie set in addition to header-based token, so
  refresh / new tab continues to work even if localStorage is wiped.
- Language detection from browser → cookie → manual override.
- All cookies are `SameSite=Lax`, `Secure` in production, opaque IDs only.

## Migration notes

- The legacy `localStorage`-based admin token still works (header path), but
  the same token is now also set as `roadcall_auth_session` HttpOnly. New code
  should rely on the cookie path; the localStorage helper can be deleted in a
  future release once the dashboards are confirmed cookie-only.
