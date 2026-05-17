"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Phone,
  MessageSquare,
  Users,
  TrendingUp,
  Clock,
  ExternalLink,
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

interface Shop {
  id: string;
  business_name: string;
  owner_name: string | null;
  business_phone: string;
  business_email: string | null;
  business_address: string | null;
  agent_greeting: string;
  voice_id: string | null;
  services_offered: string[] | null;
  service_area: string | null;
  hours_of_operation: Record<string, string> | null;
  offers_roadside: boolean;
  sip_phone_number: string | null;
  fallback_phone: string | null;
  phone_onboarding_mode: string;
  requested_area_code: string | null;
  twilio_number_status: string;
  retell_agent_id: string | null;
  retell_phone_number_id: string | null;
  retell_flow_id: string | null;
  appointment_booking_enabled: boolean;
  calcom_calendar_url: string | null;
  calcom_event_type_id: string | null;
  after_hours_enabled: boolean;
  emergency_dispatch_enabled: boolean;
  active: boolean;
  plan: string;
  total_calls_handled: number;
  total_leads_captured: number;
  total_chats_handled: number;
  total_calls_forwarded: number;
  missed_calls_recovered: number;
  appointments_booked: number;
  after_hours_jobs_captured: number;
  revenue_opportunities_cents: number;
  created_at: string;
  updated_at: string;
}

interface CallLog {
  id: string;
  caller_phone: string;
  caller_name: string | null;
  direction: string;
  channel: string;
  duration_seconds: number | null;
  intent: string | null;
  intent_summary: string | null;
  is_qualified_lead: boolean;
  lead_score: number | null;
  forwarded_to_human: boolean;
  status: string;
  started_at: string;
}

export default function ShopDetailPage() {
  const params = useParams();
  const shopId = params.id as string;
  const [shop, setShop] = useState<Shop | null>(null);
  const [calls, setCalls] = useState<CallLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [shopData, callsData] = await Promise.all([
          adminFetch<Shop>(`/shops/${shopId}`),
          adminFetch<CallLog[]>(`/shops/${shopId}/calls`),
        ]);

        setShop(shopData);
        setCalls(callsData);
      } catch (err) {
        console.error("Failed to fetch shop details:", err);
      } finally {
        setLoading(false);
      }
    }
    if (shopId) fetchData();
  }, [shopId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-white/10 animate-pulse rounded" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-16 bg-white/10 animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!shop) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Shop not found</p>
        <Link href="/admin/shops">
          <Button variant="link">Back to shops</Button>
        </Link>
      </div>
    );
  }

  const intentColors: Record<string, string> = {
    repair_request: "bg-blue-500/20 text-blue-300",
    tow_request: "bg-amber-500/20 text-amber-300",
    emergency: "bg-red-500/20 text-red-300",
    price_inquiry: "bg-green-500/20 text-green-300",
    scheduling: "bg-purple-500/20 text-purple-300",
    general_question: "bg-slate-500/20 text-slate-300",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/admin/shops">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{shop.business_name}</h1>
            <Badge variant={shop.active ? "default" : "destructive"}>
              {shop.active ? "Active" : "Inactive"}
            </Badge>
            <Badge variant="secondary">{shop.plan}</Badge>
          </div>
          <p className="text-muted-foreground">
            {shop.business_phone}
            {shop.business_address && ` · ${shop.business_address}`}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <Phone className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">
                  {shop.total_calls_handled}
                </p>
                <p className="text-xs text-muted-foreground">Calls Handled</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <Users className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">
                  {shop.total_leads_captured}
                </p>
                <p className="text-xs text-muted-foreground">Leads Captured</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <MessageSquare className="h-8 w-8 text-purple-500" />
              <div>
                <p className="text-2xl font-bold">
                  {shop.total_chats_handled}
                </p>
                <p className="text-xs text-muted-foreground">Chats Handled</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <ExternalLink className="h-8 w-8 text-amber-500" />
              <div>
                <p className="text-2xl font-bold">
                  {shop.total_calls_forwarded}
                </p>
                <p className="text-xs text-muted-foreground">
                  Forwarded to Human
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-2xl font-bold">{shop.missed_calls_recovered || 0}</p>
            <p className="text-xs text-muted-foreground">Missed Calls Recovered</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-2xl font-bold">{shop.appointments_booked || 0}</p>
            <p className="text-xs text-muted-foreground">Appointments Booked</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-2xl font-bold">{shop.after_hours_jobs_captured || 0}</p>
            <p className="text-xs text-muted-foreground">After-Hours Jobs</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-2xl font-bold">${Math.round((shop.revenue_opportunities_cents || 0) / 100).toLocaleString()}</p>
            <p className="text-xs text-muted-foreground">Revenue Opportunities</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shop Config */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">Owner:</span>{" "}
              <span className="font-medium">{shop.owner_name || "—"}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Email:</span>{" "}
              <span className="font-medium">{shop.business_email || "—"}</span>
            </div>
            <div>
              <span className="text-muted-foreground">SIP Number:</span>{" "}
              <span className="font-medium">
                {shop.sip_phone_number || "Not assigned"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Phone Setup:</span>{" "}
              <span className="font-medium">
                {shop.phone_onboarding_mode === "roadcall_twilio_number" ? "Roadcall number" : "Existing number"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Phone Status:</span>{" "}
              <span className="font-medium">{shop.twilio_number_status || "not_requested"}</span>
            </div>
            {shop.requested_area_code && (
              <div>
                <span className="text-muted-foreground">Requested Area Code:</span>{" "}
                <span className="font-medium">{shop.requested_area_code}</span>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Fallback:</span>{" "}
              <span className="font-medium">
                {shop.fallback_phone || shop.business_phone}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Roadside:</span>{" "}
              <span className="font-medium">
                {shop.offers_roadside ? "Yes" : "No"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Calendar Booking:</span>{" "}
              <span className="font-medium">{shop.appointment_booking_enabled ? "Enabled" : "Disabled"}</span>
            </div>
            {shop.calcom_calendar_url && (
              <div>
                <span className="text-muted-foreground">Calendar:</span>{" "}
                <a href={shop.calcom_calendar_url} target="_blank" rel="noreferrer" className="font-medium text-blue-400 hover:underline">
                  Open calendar
                </a>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">After Hours:</span>{" "}
              <span className="font-medium">{shop.after_hours_enabled ? "Enabled" : "Disabled"}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Emergency Dispatch:</span>{" "}
              <span className="font-medium">{shop.emergency_dispatch_enabled ? "Enabled" : "Disabled"}</span>
            </div>
            {(shop.retell_agent_id || shop.retell_flow_id || shop.retell_phone_number_id) && (
              <div className="rounded-lg bg-white/5 border border-white/10 p-2 text-xs text-slate-400">
                {shop.retell_agent_id && <div>AI agent: <span className="text-slate-200">{shop.retell_agent_id}</span></div>}
                {shop.retell_flow_id && <div>AI flow: <span className="text-slate-200">{shop.retell_flow_id}</span></div>}
                {shop.retell_phone_number_id && <div>AI phone: <span className="text-slate-200">{shop.retell_phone_number_id}</span></div>}
              </div>
            )}
            {shop.services_offered && shop.services_offered.length > 0 && (
              <div>
                <span className="text-muted-foreground">Services:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {shop.services_offered.map((s) => (
                    <Badge key={s} variant="secondary" className="text-xs">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            <div className="pt-2">
              <span className="text-muted-foreground">Greeting:</span>
              <p className="italic text-xs mt-1 bg-white/5 border border-white/10 p-2 rounded text-slate-300">
                &quot;{shop.agent_greeting}&quot;
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Call Logs */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              Recent Calls
            </CardTitle>
            <CardDescription>
              {calls.length} call{calls.length !== 1 ? "s" : ""} logged
            </CardDescription>
          </CardHeader>
          <CardContent>
            {calls.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Phone className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No calls yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                {calls.map((call) => (
                  <div
                    key={call.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-white/10 hover:bg-white/5 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          call.is_qualified_lead
                            ? "bg-green-500"
                            : "bg-slate-300"
                        }`}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">
                            {call.caller_name || call.caller_phone}
                          </span>
                          {call.intent && (
                            <Badge
                              variant="secondary"
                              className={`text-xs ${
                                intentColors[call.intent] || ""
                              }`}
                            >
                              {call.intent.replace(/_/g, " ")}
                            </Badge>
                          )}
                          {call.is_qualified_lead && (
                            <Badge
                              variant="secondary"
                              className="bg-green-100 text-green-700 text-xs"
                            >
                              Lead
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {call.intent_summary || "No summary"}
                        </p>
                      </div>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(call.started_at).toLocaleDateString()}{" "}
                        {new Date(call.started_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                      {call.lead_score !== null && (
                        <div className="mt-0.5">
                          Score: {(call.lead_score * 100).toFixed(0)}%
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
