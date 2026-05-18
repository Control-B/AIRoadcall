import fs from "node:fs";
import path from "node:path";
import { AlertTriangle, CheckCircle2, ExternalLink, Route, ShieldCheck } from "lucide-react";

export const dynamic = "force-dynamic";

type LinkFinding = { href: string; file: string };

const requiredEnv = [
  "NEXT_PUBLIC_API_URL",
  "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY",
  "MAPBOX_ACCESS_TOKEN",
  "ROADCALL_ONBOARDING_WEBHOOK_URL",
];

function walk(dir: string, predicate: (file: string) => boolean): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const filePath = path.join(dir, entry.name);
    if (entry.isDirectory()) return walk(filePath, predicate);
    return predicate(filePath) ? [filePath] : [];
  });
}

function appRoot() {
  return path.join(process.cwd(), "src", "app");
}

function srcRoot() {
  return path.join(process.cwd(), "src");
}

function routeFromPage(filePath: string) {
  const relative = path.relative(appRoot(), filePath).replace(/\\/g, "/");
  const route = relative.replace(/(^|\/)page\.tsx$/, "").replace(/(^|\/)route\.ts$/, "");
  return route ? `/${route}` : "/";
}

function routeRegex(route: string) {
  const escaped = route
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\[[^/]+?\\\]/g, "[^/]+");
  return new RegExp(`^${escaped}/?$`);
}

function normalizeHref(href: string) {
  if (!href || href.startsWith("#")) return null;
  if (/^(https?:|mailto:|tel:|sms:)/i.test(href)) return null;
  if (!href.startsWith("/")) return null;
  const route = href.split(/[?#]/)[0].replace(/\/$/, "") || "/";
  if (/\.(png|jpg|jpeg|svg|webp|ico|css|js|woff|woff2|map)$/i.test(route)) return null;
  return route.startsWith("/api") ? null : route;
}

function collectBrokenLinks(): { routes: string[]; checked: number; broken: LinkFinding[] } {
  const routes = walk(appRoot(), (file) => /\/(page\.tsx|route\.ts)$/.test(file)).map(routeFromPage);
  const pageRoutes = routes.filter((route) => !route.startsWith("/api/"));
  const matchers = pageRoutes.map(routeRegex);
  const findings: LinkFinding[] = [];

  for (const file of walk(srcRoot(), (item) => /\.(tsx|ts)$/.test(item))) {
    const text = fs.readFileSync(file, "utf8");
    const regex = /href=\{?["'`]([^"'`{}]+)["'`]\}?/g;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(text))) {
      const href = normalizeHref(match[1]);
      if (href && !matchers.some((matcher) => matcher.test(href))) {
        findings.push({ href, file: path.relative(process.cwd(), file) });
      }
    }
  }

  return { routes: pageRoutes, checked: findings.length, broken: findings };
}

function configured(value?: string) {
  const normalized = (value || "").trim().toLowerCase();
  return Boolean(
    normalized &&
      !normalized.includes("xxx") &&
      !normalized.includes("placeholder") &&
      !normalized.includes("example.") &&
      !normalized.includes("replace_with"),
  );
}

export default function AdminQAPage() {
  const linkReport = collectBrokenLinks();
  const envReport = requiredEnv.map((name) => ({ name, configured: configured(process.env[name]) }));
  const brokenCount = linkReport.broken.length;
  const missingEnvCount = envReport.filter((item) => !item.configured).length;
  const healthy = brokenCount === 0 && missingEnvCount === 0;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-blue-300">Launch QA</p>
        <h1 className="mt-2 text-3xl font-black text-white">Production readiness dashboard</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Route, link, and environment checks for the four Roadcall operating lanes. Run <code>npm run qa:production</code> in the frontend folder before deploys for the file report.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-4">
        <Metric icon={Route} label="Routes" value={linkReport.routes.length.toString()} tone="blue" />
        <Metric icon={ExternalLink} label="Broken links" value={brokenCount === 0 ? "OK" : brokenCount.toString()} tone={brokenCount ? "red" : "green"} />
        <Metric icon={ShieldCheck} label="Missing env" value={missingEnvCount.toString()} tone={missingEnvCount ? "amber" : "green"} />
        <Metric icon={healthy ? CheckCircle2 : AlertTriangle} label="Status" value={healthy ? "Ready" : "Review"} tone={healthy ? "green" : "amber"} />
      </section>

      <section className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
        <h2 className="text-lg font-bold text-white">Environment readiness</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {envReport.map((item) => (
            <div key={item.name} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
              <span className="font-mono text-slate-300">{item.name}</span>
              <span className={item.configured ? "text-emerald-300" : "text-amber-300"}>{item.configured ? "configured" : "missing"}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
        <h2 className="text-lg font-bold text-white">Broken internal links</h2>
        <div className="mt-4 space-y-2 text-sm">
          {linkReport.broken.length ? (
            linkReport.broken.slice(0, 50).map((item) => (
              <div key={`${item.file}-${item.href}`} className="rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-red-100">
                <span className="font-semibold">{item.href}</span> in <span className="font-mono text-xs">{item.file}</span>
              </div>
            ))
          ) : (
            <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-emerald-100">No broken internal page links found.</div>
          )}
        </div>
      </section>
    </div>
  );
}

function Metric({ icon: Icon, label, value, tone }: { icon: typeof Route; label: string; value: string; tone: "blue" | "green" | "amber" | "red" }) {
  const tones = {
    blue: "border-blue-300/20 bg-blue-400/10 text-blue-200",
    green: "border-emerald-300/20 bg-emerald-400/10 text-emerald-200",
    amber: "border-amber-300/20 bg-amber-400/10 text-amber-200",
    red: "border-red-300/20 bg-red-400/10 text-red-200",
  };
  return (
    <div className={`rounded-2xl border p-5 ${tones[tone]}`}>
      <Icon className="h-5 w-5" />
      <p className="mt-4 text-xs font-bold uppercase tracking-[0.18em] opacity-80">{label}</p>
      <p className="mt-1 text-2xl font-black text-white">{value}</p>
    </div>
  );
}