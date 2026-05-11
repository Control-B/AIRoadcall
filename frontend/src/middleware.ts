import { NextResponse, type NextRequest } from "next/server";

/**
 * Roadcall.ai edge middleware.
 *
 * Job: ensure every visitor has a stable anonymous correlation cookie
 * (`roadcall_client_session_id`) so we can rate-limit, debug, and log
 * without identifying the user.
 *
 * - HttpOnly + SameSite=Lax + Secure(prod).
 * - Skips static assets and the API health endpoint.
 * - Does NOT issue any auth cookie — those come from the FastAPI backend.
 */

const COOKIE_CLIENT_SESSION = "roadcall_client_session_id";
const THIRTY_DAYS = 60 * 60 * 24 * 30;

function newId(): string {
  const buf = new Uint8Array(24);
  crypto.getRandomValues(buf);
  return Array.from(buf)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function middleware(req: NextRequest) {
  const res = NextResponse.next();
  if (!req.cookies.get(COOKIE_CLIENT_SESSION)) {
    res.cookies.set({
      name: COOKIE_CLIENT_SESSION,
      value: newId(),
      maxAge: THIRTY_DAYS,
      path: "/",
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }
  return res;
}

export const config = {
  // Run on every page/route except Next internals and static assets.
  matcher: [
    "/((?!_next/|favicon|apple-touch-icon|robots.txt|sitemap.xml|.*\\.(?:png|jpg|jpeg|svg|webp|ico|css|js|woff|woff2|map)$).*)",
  ],
};
