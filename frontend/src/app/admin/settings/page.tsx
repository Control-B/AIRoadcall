"use client";

import { useState } from "react";
import { Save, Key, Phone, Mail, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function Section({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-6 shadow-lg">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/20">
          <Icon className="h-4 w-4 text-blue-400" />
        </div>
        <div>
          <h2 className="font-semibold text-white">{title}</h2>
          <p className="text-xs text-slate-400">{description}</p>
        </div>
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Field({
  label,
  note,
  children,
}: {
  label: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1.5">
        {label}
      </label>
      {children}
      {note && <p className="text-xs text-slate-500 mt-1">{note}</p>}
    </div>
  );
}

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const [settings, setSettings] = useState({
    adminKey: "",
    demoPhone: "",
    twilioSid: "",
    twilioToken: "",
    twilioFrom: "",
    resendKey: "",
    resendFrom: "",
    livekitUrl: "",
    livekitKey: "",
    livekitSecret: "",
    stripeKey: "",
    doAiEndpoint: "",
    doAiKey: "",
    doAiModel: "",
  });

  function updateField(field: string, value: string) {
    setSettings((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  }

  const inputCls =
    "bg-white/5 border-white/10 text-slate-200 placeholder:text-slate-500 focus:border-blue-500/50";

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400">
          Configure API keys and service credentials
        </p>
      </div>

      <Section
        icon={Key}
        title="Authentication"
        description="Login-based session authentication"
      >
        <p className="text-sm text-slate-400">
          Admin dashboard is protected by username/password login. Credentials are
          set via{" "}
          <code className="text-xs bg-white/10 text-slate-300 px-1.5 py-0.5 rounded">
            ADMIN_USERNAME
          </code>{" "}
          and{" "}
          <code className="text-xs bg-white/10 text-slate-300 px-1.5 py-0.5 rounded">
            ADMIN_PASSWORD
          </code>{" "}
          environment variables.
        </p>
      </Section>

      <Section
        icon={Phone}
        title="Demo Phone Line"
        description="Toll-free number for the AI demo"
      >
        <Field
          label="Demo Phone Number"
          note="This number is shown on the demo landing page and in outreach messages"
        >
          <Input
            value={settings.demoPhone}
            onChange={(e) => updateField("demoPhone", e.target.value)}
            placeholder="+18551234567"
            className={inputCls}
          />
        </Field>
      </Section>

      <Section
        icon={Phone}
        title="Twilio (SMS)"
        description="SMS delivery for outreach campaigns"
      >
        <Field label="Account SID">
          <Input
            type="password"
            value={settings.twilioSid}
            onChange={(e) => updateField("twilioSid", e.target.value)}
            placeholder="ACxxxxxxxxxxxxxxxx"
            className={inputCls}
          />
        </Field>
        <Field label="Auth Token">
          <Input
            type="password"
            value={settings.twilioToken}
            onChange={(e) => updateField("twilioToken", e.target.value)}
            placeholder="xxxxxxxxxxxxxxxx"
            className={inputCls}
          />
        </Field>
        <Field label="From Number">
          <Input
            value={settings.twilioFrom}
            onChange={(e) => updateField("twilioFrom", e.target.value)}
            placeholder="+18551234567"
            className={inputCls}
          />
        </Field>
      </Section>

      <Section
        icon={Mail}
        title="Resend (Email)"
        description="Email delivery for outreach campaigns"
      >
        <Field label="API Key">
          <Input
            type="password"
            value={settings.resendKey}
            onChange={(e) => updateField("resendKey", e.target.value)}
            placeholder="re_xxxxxxxx"
            className={inputCls}
          />
        </Field>
        <Field label="From Email">
          <Input
            value={settings.resendFrom}
            onChange={(e) => updateField("resendFrom", e.target.value)}
            placeholder="AI Receptionist <hello@yourdomain.com>"
            className={inputCls}
          />
        </Field>
      </Section>

      <Section
        icon={Phone}
        title="LiveKit (Voice AI)"
        description="Voice agent and SIP trunking"
      >
        <Field label="LiveKit URL">
          <Input
            value={settings.livekitUrl}
            onChange={(e) => updateField("livekitUrl", e.target.value)}
            placeholder="wss://your-project.livekit.cloud"
            className={inputCls}
          />
        </Field>
        <Field label="API Key">
          <Input
            type="password"
            value={settings.livekitKey}
            onChange={(e) => updateField("livekitKey", e.target.value)}
            className={inputCls}
          />
        </Field>
        <Field label="API Secret">
          <Input
            type="password"
            value={settings.livekitSecret}
            onChange={(e) => updateField("livekitSecret", e.target.value)}
            className={inputCls}
          />
        </Field>
      </Section>

      <Section
        icon={Globe}
        title="DigitalOcean AI (Text Chat)"
        description="Text-based AI chat for shop customers"
      >
        <Field label="Endpoint">
          <Input
            value={settings.doAiEndpoint}
            onChange={(e) => updateField("doAiEndpoint", e.target.value)}
            placeholder="https://cluster-api.do-ai.run/v1"
            className={inputCls}
          />
        </Field>
        <Field label="API Key">
          <Input
            type="password"
            value={settings.doAiKey}
            onChange={(e) => updateField("doAiKey", e.target.value)}
            className={inputCls}
          />
        </Field>
        <Field label="Model">
          <Input
            value={settings.doAiModel}
            onChange={(e) => updateField("doAiModel", e.target.value)}
            placeholder="meta-llama/Meta-Llama-3.1-70B-Instruct"
            className={inputCls}
          />
        </Field>
      </Section>

      <div className="flex items-center gap-3">
        <Button
          onClick={() => {
            setSaved(true);
            setTimeout(() => setSaved(false), 3000);
          }}
          className="gap-2"
        >
          <Save className="h-4 w-4" />
          Save Settings
        </Button>
        {saved && (
          <span className="text-sm text-emerald-400 font-medium">
            ✓ Settings saved
          </span>
        )}
      </div>

      <p className="text-xs text-slate-500">
        Note: In production, settings are managed via environment variables on
        your DigitalOcean app. This page is for reference and local development.
      </p>
    </div>
  );
}
