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
import { adminFetch } from "@/lib/admin-auth";

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
  draft: { icon: Clock, color: "bg-slate-500/20 text-slate-300", label: "Draft" },
  scheduled: {
    icon: Clock,
    color: "bg-amber-500/20 text-amber-300",
    label: "Scheduled",
  },
  sending: {
    icon: Send,
    color: "bg-blue-500/20 text-blue-300",
    label: "Sending",
  },
  completed: {
    icon: CheckCircle2,
    color: "bg-emerald-500/20 text-emerald-300",
    label: "Completed",
  },
  paused: {
    icon: Pause,
    color: "bg-amber-500/20 text-amber-300",
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
        const data = await adminFetch<Campaign[]>("/outreach/campaigns");
        setCampaigns(data);
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
          <h1 className="text-2xl font-bold text-white">Outreach Campaigns</h1>
          <p className="text-slate-400">
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
        {[
          { label: "Total Campaigns", value: campaigns.length, color: "text-white" },
          { label: "Messages Sent", value: campaigns.reduce((s,c)=>s+c.total_sent,0).toLocaleString(), color: "text-white" },
          { label: "Demo Calls", value: campaigns.reduce((s,c)=>s+c.total_demo_calls,0), color: "text-white" },
          { label: "Signups", value: campaigns.reduce((s,c)=>s+c.total_signups,0), color: "text-emerald-400" },
        ].map(item => (
          <div key={item.label} className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-5 text-center">
            <p className={`text-3xl font-bold ${item.color}`}>{item.value}</p>
            <p className="text-xs text-slate-400 mt-1">{item.label}</p>
          </div>
        ))}
      </div>

      {/* Campaign List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-2xl border border-white/5 bg-slate-900/60" />
          ))}
        </div>
      ) : campaigns.length === 0 ? (
          <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 py-16 text-center">
              <Megaphone className="h-12 w-12 text-slate-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2 text-slate-200">No campaigns yet</h3>
              <p className="text-slate-400 mb-4">
              Create your first outreach campaign to start acquiring shop
              customers.
            </p>
            <Link href="/admin/outreach/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create First Campaign
              </Button>
            </Link>
          </div>
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
                <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-4 hover:border-blue-500/30 hover:bg-slate-900 transition-all cursor-pointer">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                        <ChannelIcon className="h-5 w-5 text-blue-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-slate-100">{campaign.name}</h3>
                          <Badge
                            variant="secondary"
                            className={status.color}
                          >
                            {status.label}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-400 mt-0.5">
                          {campaign.description ||
                            campaign.body_template.slice(0, 80) + "..."}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-8">
                      <div className="text-right hidden md:block space-y-1">
                        <div className="text-sm">
                          <span className="font-medium text-slate-200">
                            {campaign.total_sent.toLocaleString()}
                          </span>{" "}
                          <span className="text-slate-500">
                            / {campaign.total_targeted.toLocaleString()} sent
                          </span>
                        </div>
                        <div className="flex gap-4 text-xs text-slate-500">
                          <span>
                            {campaign.total_replied} replied
                          </span>
                          <span>
                            {campaign.total_demo_calls} demos
                          </span>
                          <span className="text-emerald-400 font-medium">
                            {campaign.total_signups} signups
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-slate-500" />
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
