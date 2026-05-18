#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const appDir = path.join(root, "frontend", "src", "app");
const frontendSrc = path.join(root, "frontend", "src");
const outputDir = path.join(root, "docs");

const requiredEnv = [
  "NEXT_PUBLIC_API_URL",
  "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY",
  "MAPBOX_ACCESS_TOKEN",
  "ROADCALL_ONBOARDING_WEBHOOK_URL",
];

function walk(dir, predicate = () => true) {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const filePath = path.join(dir, entry.name);
    if (entry.isDirectory()) return walk(filePath, predicate);
    return predicate(filePath) ? [filePath] : [];
  });
}

function routeFromPage(filePath) {
  const relative = path.relative(appDir, filePath).replace(/\\/g, "/");
  const route = relative.replace(/(^|\/)page\.tsx$/, "").replace(/(^|\/)route\.ts$/, "");
  return route ? `/${route}` : "/";
}

function routeRegex(route) {
  const escaped = route
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\[[^/]+?\\\]/g, "[^/]+");
  return new RegExp(`^${escaped}/?$`);
}

function normalizeHref(href) {
  if (!href || href.startsWith("#")) return null;
  if (/^(https?:|mailto:|tel:|sms:)/i.test(href)) return null;
  if (!href.startsWith("/")) return null;
  const withoutQuery = href.split(/[?#]/)[0].replace(/\/$/, "") || "/";
  if (/\.(png|jpg|jpeg|svg|webp|ico|css|js|woff|woff2|map)$/i.test(withoutQuery)) return null;
  return withoutQuery.startsWith("/api") ? null : withoutQuery;
}

function collectRoutes() {
  return walk(appDir, (file) => /\/(page\.tsx|route\.ts)$/.test(file)).map(routeFromPage);
}

function collectInternalHrefs() {
  const files = walk(frontendSrc, (file) => /\.(tsx|ts)$/.test(file));
  const hrefs = [];
  for (const file of files) {
    const text = fs.readFileSync(file, "utf8");
    const regex = /href=\{?["'`]([^"'`{}]+)["'`]\}?/g;
    let match;
    while ((match = regex.exec(text))) {
      const href = normalizeHref(match[1]);
      if (href) hrefs.push({ href, file: path.relative(root, file) });
    }
  }
  return hrefs;
}

function envConfigured(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return Boolean(
    normalized &&
      !normalized.includes("xxx") &&
      !normalized.includes("placeholder") &&
      !normalized.includes("example.") &&
      !normalized.includes("replace_with"),
  );
}

function main() {
  const routes = collectRoutes();
  const pageRoutes = routes.filter((route) => !route.startsWith("/api/"));
  const routeMatchers = pageRoutes.map((route) => ({ route, regex: routeRegex(route) }));
  const hrefs = collectInternalHrefs();
  const brokenLinks = hrefs.filter(({ href }) => !routeMatchers.some(({ regex }) => regex.test(href)));
  const env = requiredEnv.map((name) => ({ name, configured: envConfigured(process.env[name]) }));

  const report = {
    generated_at: new Date().toISOString(),
    summary: {
      page_routes: pageRoutes.length,
      internal_links_checked: hrefs.length,
      broken_links: brokenLinks.length,
      missing_env_vars: env.filter((item) => !item.configured).length,
    },
    broken_links: brokenLinks,
    env,
    recommended_commands: [
      "cd frontend && npm run build",
      "cd backend && uv run pytest",
      "cd frontend && npm run qa:production",
    ],
  };

  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(path.join(outputDir, "production-readiness-report.json"), `${JSON.stringify(report, null, 2)}\n`);
  fs.writeFileSync(
    path.join(outputDir, "production-readiness-report.md"),
    [
      "# Roadcall Production Readiness Report",
      "",
      `Generated: ${report.generated_at}`,
      "",
      `- Page routes: ${report.summary.page_routes}`,
      `- Internal links checked: ${report.summary.internal_links_checked}`,
      `- Broken links: ${report.summary.broken_links}`,
      `- Missing env vars: ${report.summary.missing_env_vars}`,
      "",
      "## Broken Links",
      ...(brokenLinks.length ? brokenLinks.map((item) => `- ${item.href} in ${item.file}`) : ["- None found"]),
      "",
      "## Environment",
      ...env.map((item) => `- ${item.configured ? "OK" : "MISSING"}: ${item.name}`),
      "",
    ].join("\n"),
  );

  console.log(JSON.stringify(report.summary, null, 2));
  process.exitCode = brokenLinks.length > 0 || env.some((item) => !item.configured) ? 1 : 0;
}

main();