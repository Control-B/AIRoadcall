"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus,
  Megaphone,
  Send,
  Clock,
  CheckCircle2,
  Pause,
  ChevronRight,
  MessageSquare,
  Mail,
  Phone,
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY || "change-this-to-a-secure-admin-key";

interface Campaign {
  id: string;
  name: string;
  description: string | null;
  channel: string;
  status: string;
  body_template: string;
  total_targeted: number;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_replied: number;
  total_demo_calls: number;
  total_signups: number;
  created_at: string;
}

const statusConfig: Record<
  string,
  { icon: React.ElementType; color: string; label: string }
> = {
  draft: { icon: Clock, color: "bg-slate-100 text-slate-700", label: "Draft" },
  scheduled: {
    icon: Clock,
    color: "bg-amber-100 text-amber-700",
    label: "Scheduled",
  },
  sending: {
    icon: Send,
    color: "bg-blue-100 text-blue-700",
    label: "Sending",
  },
  completed: {
    icon: CheckCircle2,
    color: "bg-green-100 text-green-700",
    label: "Completed",
  },
  paused: {
    icon: Pause,
    color: "bg-amber-100 text-amber-700",
    label: "Paused",
  },
};

const channelIcons: Record<string, React.ElementType> = {
  sms: MessageSquare,
  email: Mail,
  voice: Phone,
};

export default function OutreachPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCampaigns() {
      try {
        const res = await fetch(`${API_BASE}/outreach/campaigns`, {
          headers: { "x-admin-key": ADMIN_KEY },
        });
        if (res.ok) {
          setCampaigns(await res.json());
        }
      } catch (err) {
        console.error("Failed to fetch campaigns:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchCampaigns();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Outreach Campaigns</h1>
          <p className="text-muted-foreground">
            SMS & email campaigns to acquire shop customers
          </p>
        </div>
        <Link href="/admin/outreach/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Campaign
          </Button>
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-3xl font-bold">
              {campaigns.length}
            </p>
            <p className="text-xs text-muted-foreground">Total Campaigns</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-3xl font-bold">
              {campaigns
                .reduce((s, c) => s + c.total_sent, 0)
                .toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground">Messages Sent</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-3xl font-bold">
              {campaigns.reduce((s, c) => s + c.total_demo_calls, 0)}
            </p>
            <p className="text-xs text-muted-foreground">Demo Calls</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-3xl font-bold text-green-600">
              {campaigns.reduce((s, c) => s + c.total_signups, 0)}
            </p>
            <p className="text-xs text-muted-foreground">Signups</p>
          </CardContent>
        </Card>
      </div>

      {/* Campaign List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-16 bg-slate-100 animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : campaigns.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <Megaphone className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No campaigns yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first outreach campaign to start acquiring shop
              customers.
            </p>
            <Link href="/admin/outreach/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create First Campaign
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {campaigns.map((campaign) => {
            const ChannelIcon = channelIcons[campaign.channel] || MessageSquare;
            const status = statusConfig[campaign.status] || statusConfig.draft;

            return (
              <Link
                key={campaign.id}
                href={`/admin/outreach/${campaign.id}`}
              >
                <Card className="hover:border-blue-200 hover:shadow-md transition-all cursor-pointer">
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                          <ChannelIcon className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold">{campaign.name}</h3>
                            <Badge
                              variant="secondary"
                              className={status.color}
                            >
                              {status.label}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mt-0.5">
                            {campaign.description ||
                              campaign.body_template.slice(0, 80) + "..."}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-8">
                        <div className="text-right hidden md:block space-y-1">
                          <div className="text-sm">
                            <span className="font-medium">
                              {campaign.total_sent.toLocaleString()}
                            </span>{" "}
                            <span className="text-muted-foreground">
                              / {campaign.total_targeted.toLocaleString()} sent
                            </span>
                          </div>
                          <div className="flex gap-4 text-xs text-muted-foreground">
                            <span>
                              {campaign.total_replied} replied
                            </span>
                            <span>
                              {campaign.total_demo_calls} demos
                            </span>
                            <span className="text-green-600 font-medium">
                              {campaign.total_signups} signups
                            </span>
                          </div>
                        </div>
                        <ChevronRight className="h-5 w-5 text-muted-foreground" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
