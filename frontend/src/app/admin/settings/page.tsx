"use client";

import { useState } from "react";
import { Save, Key, Phone, Mail, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

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

  function handleSave() {
    // In production, this would save to the backend
    // For now, just show the confirmation
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Configure API keys and service credentials
        </p>
      </div>

      {/* Admin Auth */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Authentication
          </CardTitle>
          <CardDescription>
            Admin API key for dashboard access
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Admin API Key</label>
            <Input
              type="password"
              value={settings.adminKey}
              onChange={(e) => updateField("adminKey", e.target.value)}
              placeholder="Set in ADMIN_API_KEY env var"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Used as X-Admin-Key header for all admin API calls
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Demo Line */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Demo Phone Line
          </CardTitle>
          <CardDescription>
            Toll-free number for the AI demo
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Demo Phone Number</label>
            <Input
              value={settings.demoPhone}
              onChange={(e) => updateField("demoPhone", e.target.value)}
              placeholder="+18551234567"
            />
            <p className="text-xs text-muted-foreground mt-1">
              This number is shown on the demo landing page and in outreach
              messages
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Twilio */}
      <Card>
        <CardHeader>
          <CardTitle>Twilio (SMS)</CardTitle>
          <CardDescription>
            SMS delivery for outreach campaigns
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Account SID</label>
            <Input
              type="password"
              value={settings.twilioSid}
              onChange={(e) => updateField("twilioSid", e.target.value)}
              placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Auth Token</label>
            <Input
              type="password"
              value={settings.twilioToken}
              onChange={(e) => updateField("twilioToken", e.target.value)}
              placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            />
          </div>
          <div>
            <label className="text-sm font-medium">From Number</label>
            <Input
              value={settings.twilioFrom}
              onChange={(e) => updateField("twilioFrom", e.target.value)}
              placeholder="+18551234567"
            />
          </div>
        </CardContent>
      </Card>

      {/* Resend */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Resend (Email)
          </CardTitle>
          <CardDescription>
            Email delivery for outreach campaigns
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">API Key</label>
            <Input
              type="password"
              value={settings.resendKey}
              onChange={(e) => updateField("resendKey", e.target.value)}
              placeholder="re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            />
          </div>
          <div>
            <label className="text-sm font-medium">From Email</label>
            <Input
              value={settings.resendFrom}
              onChange={(e) => updateField("resendFrom", e.target.value)}
              placeholder="AI Receptionist <hello@yourdomain.com>"
            />
          </div>
        </CardContent>
      </Card>

      {/* LiveKit */}
      <Card>
        <CardHeader>
          <CardTitle>LiveKit (Voice AI)</CardTitle>
          <CardDescription>
            Voice agent and SIP trunking
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">LiveKit URL</label>
            <Input
              value={settings.livekitUrl}
              onChange={(e) => updateField("livekitUrl", e.target.value)}
              placeholder="wss://your-project.livekit.cloud"
            />
          </div>
          <div>
            <label className="text-sm font-medium">API Key</label>
            <Input
              type="password"
              value={settings.livekitKey}
              onChange={(e) => updateField("livekitKey", e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium">API Secret</label>
            <Input
              type="password"
              value={settings.livekitSecret}
              onChange={(e) => updateField("livekitSecret", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* DO AI */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            DigitalOcean AI (Text Chat)
          </CardTitle>
          <CardDescription>
            Text-based AI chat for shop customers
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Endpoint</label>
            <Input
              value={settings.doAiEndpoint}
              onChange={(e) => updateField("doAiEndpoint", e.target.value)}
              placeholder="https://cluster-api.do-ai.run/v1"
            />
          </div>
          <div>
            <label className="text-sm font-medium">API Key</label>
            <Input
              type="password"
              value={settings.doAiKey}
              onChange={(e) => updateField("doAiKey", e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Model</label>
            <Input
              value={settings.doAiModel}
              onChange={(e) => updateField("doAiModel", e.target.value)}
              placeholder="meta-llama/Meta-Llama-3.1-70B-Instruct"
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} className="gap-2">
          <Save className="h-4 w-4" />
          Save Settings
        </Button>
        {saved && (
          <span className="text-sm text-green-600 font-medium">
            ✓ Settings saved
          </span>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        Note: In production, these settings are managed via environment
        variables on your DigitalOcean app. This page is for reference and
        local development.
      </p>
    </div>
  );
}
