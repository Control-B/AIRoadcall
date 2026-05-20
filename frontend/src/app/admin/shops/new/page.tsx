"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { adminFetch } from "@/lib/admin-auth";

export default function NewShopPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    business_name: "",
    owner_name: "",
    business_phone: "",
    business_email: "",
    business_address: "",
    services_offered: "",
    service_area: "",
    offers_roadside: false,
    fallback_phone: "",
    agent_greeting: "Thank you for calling. How can I help you today?",
    plan: "standard",
  });

  function updateField(field: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload = {
        ...form,
        services_offered: form.services_offered
          ? form.services_offered.split(",").map((s) => s.trim())
          : null,
      };

      const shop = await adminFetch<{ id: string }>("/shops/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.push(`/admin/shops/${shop.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/admin/shops">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Add New Shop</h1>
          <p className="text-muted-foreground">
            Onboard a new shop to AI Receptionist
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Business Info */}
        <Card>
          <CardHeader>
            <CardTitle>Business Information</CardTitle>
            <CardDescription>
              Basic details about the shop
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">
                Business Name <span className="text-red-500">*</span>
              </label>
              <Input
                value={form.business_name}
                onChange={(e) => updateField("business_name", e.target.value)}
                placeholder="Mike's Diesel Repair"
                required
              />
            </div>
            <div>
              <label className="text-sm font-medium">Owner Name</label>
              <Input
                value={form.owner_name}
                onChange={(e) => updateField("owner_name", e.target.value)}
                placeholder="Mike Johnson"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">
                  Business Phone <span className="text-red-500">*</span>
                </label>
                <Input
                  value={form.business_phone}
                  onChange={(e) =>
                    updateField("business_phone", e.target.value)
                  }
                  placeholder="+18175551234"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <Input
                  value={form.business_email}
                  onChange={(e) =>
                    updateField("business_email", e.target.value)
                  }
                  placeholder="mike@dieselrepair.com"
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Address</label>
              <Input
                value={form.business_address}
                onChange={(e) =>
                  updateField("business_address", e.target.value)
                }
                placeholder="123 Main St, Dallas, TX 75201"
              />
            </div>
          </CardContent>
        </Card>

        {/* Service Info */}
        <Card>
          <CardHeader>
            <CardTitle>Services</CardTitle>
            <CardDescription>
              What services does this shop offer? The AI will use this info.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">
                Services Offered (comma-separated)
              </label>
              <Input
                value={form.services_offered}
                onChange={(e) =>
                  updateField("services_offered", e.target.value)
                }
                placeholder="Diesel repair, Truck towing, Trailer repair, Roadside service"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Service Area</label>
              <Input
                value={form.service_area}
                onChange={(e) => updateField("service_area", e.target.value)}
                placeholder="Dallas-Fort Worth metro, 50 mile radius"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="roadside"
                checked={form.offers_roadside}
                onChange={(e) =>
                  updateField("offers_roadside", e.target.checked)
                }
                className="rounded"
              />
              <label htmlFor="roadside" className="text-sm font-medium">
                Offers mobile roadside service
              </label>
            </div>
          </CardContent>
        </Card>

        {/* AI Config */}
        <Card>
          <CardHeader>
            <CardTitle>AI Configuration</CardTitle>
            <CardDescription>
              How the AI receptionist behaves
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Greeting Message</label>
              <Input
                value={form.agent_greeting}
                onChange={(e) =>
                  updateField("agent_greeting", e.target.value)
                }
                placeholder="Thank you for calling Mike's Diesel Repair. How can I help you?"
              />
              <p className="text-xs text-muted-foreground mt-1">
                The first thing the AI says when answering a call
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">
                Fallback Phone (transfer to human)
              </label>
              <Input
                value={form.fallback_phone}
                onChange={(e) =>
                  updateField("fallback_phone", e.target.value)
                }
                placeholder="+18175551234"
              />
              <p className="text-xs text-muted-foreground mt-1">
                When a caller asks to speak to a human, the AI transfers here
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">Plan</label>
              <select
                value={form.plan}
                onChange={(e) => updateField("plan", e.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="standard">Standard ($299/mo)</option>
                <option value="premium">Premium ($499/mo)</option>
                <option value="advanced">Advanced ($999/mo)</option>
              </select>
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
            {saving ? "Creating..." : "Create Shop"}
          </Button>
          <Link href="/admin/shops">
            <Button variant="outline">Cancel</Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
