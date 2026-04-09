"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Send,
  MessageSquare,
  Mail,
  Phone,
  Eye,
  Save,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { adminFetch } from "@/lib/admin-auth";

const SMS_TEMPLATES = [
  {
    name: "Cold Intro — Demo CTA",
    body: `Hi {business_name}! 👋 We built an AI receptionist that answers your shop's calls 24/7, qualifies leads, and books appointments. Want to hear it? Call our demo line: {demo_number} — it's free, takes 60 seconds. Reply STOP to opt out.`,
  },
  {
    name: "After-Hours Focus",
    body: `{business_name}: Are you missing calls after hours? Our AI picks up every call 24/7 and sends you the lead details instantly. Hear it in action: {demo_number}. Plans start at $99/mo. Reply STOP to opt out.`,
  },
  {
    name: "Roadside Shops",
    body: `{business_name}: When a trucker calls for roadside help at 2 AM, are you picking up? Our AI answers every emergency call, gets their location, and dispatches you. Try it: {demo_number}. Reply STOP to opt out.`,
  },
];

const EMAIL_TEMPLATES = [
  {
    name: "Professional Intro",
    body: `<h2>Stop Missing Calls. Start Catching Leads.</h2>
<p>Hi {business_name},</p>
<p>We built an AI receptionist specifically for truck repair and mechanic shops. It:</p>
<ul>
<li>✅ Answers every call 24/7 — even at 3 AM</li>
<li>✅ Qualifies leads and captures vehicle info</li>
<li>✅ Books appointments on your schedule</li>
<li>✅ Sounds like a real employee who knows your business</li>
</ul>
<p><strong>Want to hear it?</strong> Call our demo line: <a href="tel:{demo_number}">{demo_number}</a></p>
<p>Or visit <a href="{demo_url}">{demo_url}</a> to learn more.</p>
<p>Plans start at just $99/month. No contracts, cancel anytime.</p>`,
  },
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewResult, setPreviewResult] = useState<{
    total_matching: number;
    sample: Record<string, unknown>[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    description: "",
    channel: "sms",
    subject: "",
    body_template: SMS_TEMPLATES[0].body,
    // Segment filters
    states: "",
    roadside_only: false,
    min_rating: "",
    min_reviews: "",
    has_website: false,
    limit: "",
  });

  function updateField(field: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function applyTemplate(body: string) {
    setForm((prev) => ({ ...prev, body_template: body }));
  }

  function buildSegmentFilters() {
    const filters: Record<string, unknown> = {};
    if (form.states) {
      filters.states = form.states.split(",").map((s) => s.trim().toUpperCase());
    }
    if (form.roadside_only) filters.roadside_only = true;
    if (form.min_rating) filters.min_rating = parseFloat(form.min_rating);
    if (form.min_reviews) filters.min_reviews = parseInt(form.min_reviews);
    if (form.has_website) filters.has_website = true;
    if (form.limit) filters.limit = parseInt(form.limit);
    return Object.keys(filters).length > 0 ? filters : null;
  }

  async function handlePreview() {
    setPreviewing(true);
    setPreviewResult(null);
    try {
      const filters = buildSegmentFilters() || {};
      const data = await adminFetch<{ total_matching: number; sample: Record<string, unknown>[] }>("/outreach/segment/preview", {
        method: "POST",
        body: JSON.stringify(filters),
      });
      setPreviewResult(data);
    } catch (err) {
      console.error("Preview failed:", err);
    } finally {
      setPreviewing(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload = {
        name: form.name,
        description: form.description || null,
        channel: form.channel,
        subject: form.subject || null,
        body_template: form.body_template,
        segment_filters: buildSegmentFilters(),
      };

      const campaign = await adminFetch<{ id: string }>("/outreach/campaigns", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.push(`/admin/outreach/${campaign.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  const templates = form.channel === "sms" ? SMS_TEMPLATES : EMAIL_TEMPLATES;

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/admin/outreach">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">New Campaign</h1>
          <p className="text-muted-foreground">
            Create an outreach campaign to acquire shop customers
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basics */}
        <Card>
          <CardHeader>
            <CardTitle>Campaign Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">
                Campaign Name <span className="text-red-500">*</span>
              </label>
              <Input
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                placeholder="TX/FL Roadside Shops — SMS Intro"
                required
              />
            </div>
            <div>
              <label className="text-sm font-medium">Description</label>
              <Input
                value={form.description}
                onChange={(e) => updateField("description", e.target.value)}
                placeholder="First touch SMS to roadside shops in Texas and Florida"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Channel</label>
              <div className="flex gap-2 mt-1">
                {[
                  { value: "sms", icon: MessageSquare, label: "SMS" },
                  { value: "email", icon: Mail, label: "Email" },
                  { value: "voice", icon: Phone, label: "Voice" },
                ].map((ch) => (
                  <button
                    key={ch.value}
                    type="button"
                    onClick={() => updateField("channel", ch.value)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                      form.channel === ch.value
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <ch.icon className="h-4 w-4" />
                    {ch.label}
                  </button>
                ))}
              </div>
            </div>
            {form.channel === "email" && (
              <div>
                <label className="text-sm font-medium">Email Subject</label>
                <Input
                  value={form.subject}
                  onChange={(e) => updateField("subject", e.target.value)}
                  placeholder="AI Receptionist for {business_name} — Never Miss a Call"
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Targeting */}
        <Card>
          <CardHeader>
            <CardTitle>Targeting</CardTitle>
            <CardDescription>
              Filter which mechanics receive this campaign
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">
                States (comma-separated, e.g. TX, FL, GA)
              </label>
              <Input
                value={form.states}
                onChange={(e) => updateField("states", e.target.value)}
                placeholder="Leave empty for all states"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Min Rating</label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="5"
                  value={form.min_rating}
                  onChange={(e) => updateField("min_rating", e.target.value)}
                  placeholder="e.g. 4.0"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Min Reviews</label>
                <Input
                  type="number"
                  min="0"
                  value={form.min_reviews}
                  onChange={(e) => updateField("min_reviews", e.target.value)}
                  placeholder="e.g. 10"
                />
              </div>
            </div>
            <div className="flex gap-6">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="roadside"
                  checked={form.roadside_only}
                  onChange={(e) =>
                    updateField("roadside_only", e.target.checked)
                  }
                  className="rounded"
                />
                <label htmlFor="roadside" className="text-sm">
                  Roadside shops only
                </label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="has_website"
                  checked={form.has_website}
                  onChange={(e) =>
                    updateField("has_website", e.target.checked)
                  }
                  className="rounded"
                />
                <label htmlFor="has_website" className="text-sm">
                  Has website
                </label>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">
                Limit (max recipients)
              </label>
              <Input
                type="number"
                min="1"
                value={form.limit}
                onChange={(e) => updateField("limit", e.target.value)}
                placeholder="Leave empty for no limit"
              />
            </div>

            {/* Preview */}
            <div className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={handlePreview}
                disabled={previewing}
                className="gap-2"
              >
                <Eye className="h-4 w-4" />
                {previewing ? "Loading..." : "Preview Segment"}
              </Button>

              {previewResult && (
                <div className="mt-3 bg-slate-50 rounded-lg p-4">
                  <p className="font-medium">
                    {previewResult.total_matching.toLocaleString()} mechanics
                    match
                  </p>
                  {previewResult.sample.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs text-muted-foreground">
                        Sample:
                      </p>
                      {previewResult.sample.slice(0, 5).map((m, i) => (
                        <div
                          key={i}
                          className="text-xs flex gap-2 text-muted-foreground"
                        >
                          <span className="font-medium text-foreground">
                            {m.company_name as string}
                          </span>
                          <span>{m.phone as string}</span>
                          <span className="truncate">
                            {m.address as string}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Message Content */}
        <Card>
          <CardHeader>
            <CardTitle>Message Content</CardTitle>
            <CardDescription>
              Use {"{business_name}"}, {"{phone}"}, {"{address}"},{" "}
              {"{demo_number}"}, {"{demo_url}"} as template variables
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Template picker */}
            <div>
              <label className="text-sm font-medium mb-2 block">
                Quick Templates
              </label>
              <div className="flex flex-wrap gap-2">
                {templates.map((t) => (
                  <button
                    key={t.name}
                    type="button"
                    onClick={() => applyTemplate(t.body)}
                    className="text-xs px-3 py-1.5 rounded-full border hover:bg-blue-50 hover:border-blue-200 transition-colors"
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium">
                Message Body <span className="text-red-500">*</span>
              </label>
              <textarea
                value={form.body_template}
                onChange={(e) =>
                  updateField("body_template", e.target.value)
                }
                rows={form.channel === "email" ? 12 : 5}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring mt-1 font-mono"
                required
              />
              {form.channel === "sms" && (
                <p className="text-xs text-muted-foreground mt-1">
                  {form.body_template.length} / 160 chars
                  {form.body_template.length > 160 && (
                    <span className="text-amber-600">
                      {" "}
                      (will send as{" "}
                      {Math.ceil(form.body_template.length / 160)} segments)
                    </span>
                  )}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {error && (
          <div className="bg-red-50 text-red-700 rounded-lg p-4 text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <Button type="submit" disabled={saving} className="gap-2">
            <Save className="h-4 w-4" />
            {saving ? "Creating..." : "Create Campaign"}
          </Button>
          <Link href="/admin/outreach">
            <Button variant="outline">Cancel</Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
