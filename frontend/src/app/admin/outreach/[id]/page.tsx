"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Send,
  Play,
  Pause,
  BarChart3,
  MessageSquare,
  Users,
  Phone,
  UserPlus,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { adminFetch } from "@/lib/admin-auth";

interface Campaign {
  id: string;
  name: string;
  description: string | null;
  channel: string;
  status: string;
  subject: string | null;
  body_template: string;
  segment_filters: Record<string, unknown> | null;
  total_targeted: number;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_replied: number;
  total_demo_calls: number;
  total_signups: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

function StatBox({
  label,
  value,
  rate,
  color = "blue",
}: {
  label: string;
  value: number;
  rate?: number;
  color?: string;
}) {
  return (
    <div className="text-center p-4 rounded-lg bg-slate-50">
      <p className="text-2xl font-bold">{value.toLocaleString()}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
      {rate !== undefined && (
        <p className="text-xs font-medium mt-1 text-blue-600">
          {(rate * 100).toFixed(1)}%
        </p>
      )}
    </div>
  );
}

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id as string;
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [processing, setProcessing] = useState(false);

  async function fetchCampaign() {
    try {
      const data = await adminFetch<Campaign>(`/outreach/campaigns/${campaignId}`);
      setCampaign(data);
    } catch (err) {
      console.error("Failed to fetch campaign:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (campaignId) fetchCampaign();
  }, [campaignId]);

  async function handleSend() {
    if (
      !confirm(
        "This will queue messages for all targeted mechanics. Continue?"
      )
    )
      return;
    setSending(true);
    try {
      await adminFetch(`/outreach/campaigns/${campaignId}/send`, {
        method: "POST",
      });
      await fetchCampaign();
    } catch (err) {
      console.error("Send failed:", err);
    } finally {
      setSending(false);
    }
  }

  async function handleProcess() {
    setProcessing(true);
    try {
      const result = await adminFetch<{ batch_sent: number; batch_failed: number; remaining: number }>(
        `/outreach/campaigns/${campaignId}/process?batch_size=100`,
        { method: "POST" }
      );
      alert(
        `Sent: ${result.batch_sent}, Failed: ${result.batch_failed}, Remaining: ${result.remaining}`
      );
      await fetchCampaign();
    } catch (err) {
      console.error("Process failed:", err);
    } finally {
      setProcessing(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-slate-100 animate-pulse rounded" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="h-20 bg-slate-100 animate-pulse rounded-lg"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Campaign not found</p>
      </div>
    );
  }

  const totalSent = campaign.total_sent || 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/admin/outreach">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{campaign.name}</h1>
              <Badge
                variant="secondary"
                className={
                  campaign.status === "completed"
                    ? "bg-green-100 text-green-700"
                    : campaign.status === "sending"
                    ? "bg-blue-100 text-blue-700"
                    : ""
                }
              >
                {campaign.status}
              </Badge>
              <Badge variant="outline">{campaign.channel.toUpperCase()}</Badge>
            </div>
            <p className="text-muted-foreground">
              {campaign.description || "No description"}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {campaign.status === "draft" && (
            <Button
              onClick={handleSend}
              disabled={sending}
              className="gap-2 bg-green-600 hover:bg-green-700"
            >
              {sending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {sending ? "Queuing..." : "Queue & Send"}
            </Button>
          )}
          {campaign.status === "sending" && (
            <Button
              onClick={handleProcess}
              disabled={processing}
              className="gap-2"
            >
              {processing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {processing ? "Processing..." : "Process Next Batch"}
            </Button>
          )}
        </div>
      </div>

      {/* Funnel Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <StatBox label="Targeted" value={campaign.total_targeted} />
        <StatBox label="Sent" value={campaign.total_sent} />
        <StatBox
          label="Delivered"
          value={campaign.total_delivered}
          rate={campaign.total_delivered / totalSent}
        />
        <StatBox
          label="Opened"
          value={campaign.total_opened}
          rate={campaign.total_opened / totalSent}
        />
        <StatBox
          label="Clicked"
          value={campaign.total_clicked}
          rate={campaign.total_clicked / totalSent}
        />
        <StatBox
          label="Replied"
          value={campaign.total_replied}
          rate={campaign.total_replied / totalSent}
        />
        <StatBox
          label="Demo Calls"
          value={campaign.total_demo_calls}
          rate={campaign.total_demo_calls / totalSent}
        />
        <StatBox
          label="Signups"
          value={campaign.total_signups}
          rate={campaign.total_signups / totalSent}
          color="green"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Message Preview */}
        <Card>
          <CardHeader>
            <CardTitle>Message Template</CardTitle>
          </CardHeader>
          <CardContent>
            {campaign.subject && (
              <div className="mb-3">
                <span className="text-sm text-muted-foreground">
                  Subject:{" "}
                </span>
                <span className="font-medium">{campaign.subject}</span>
              </div>
            )}
            <div className="bg-slate-50 rounded-lg p-4 text-sm whitespace-pre-wrap font-mono">
              {campaign.body_template}
            </div>
          </CardContent>
        </Card>

        {/* Segment Info */}
        <Card>
          <CardHeader>
            <CardTitle>Segment Filters</CardTitle>
          </CardHeader>
          <CardContent>
            {campaign.segment_filters ? (
              <div className="space-y-2 text-sm">
                {Object.entries(campaign.segment_filters).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-muted-foreground">
                      {key.replace(/_/g, " ")}:
                    </span>
                    <span className="font-medium">
                      {Array.isArray(val) ? val.join(", ") : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                No filters — targets all mechanics
              </p>
            )}
            <div className="mt-4 pt-4 border-t text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created:</span>
                <span>
                  {new Date(campaign.created_at).toLocaleDateString()}
                </span>
              </div>
              {campaign.started_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Started:</span>
                  <span>
                    {new Date(campaign.started_at).toLocaleDateString()}
                  </span>
                </div>
              )}
              {campaign.completed_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Completed:</span>
                  <span>
                    {new Date(campaign.completed_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
