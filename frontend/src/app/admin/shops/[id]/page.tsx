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
  active: boolean;
  plan: string;
  total_calls_handled: number;
  total_leads_captured: number;
  total_chats_handled: number;
  total_calls_forwarded: number;
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
        <div className="h-8 w-48 bg-slate-100 animate-pulse rounded" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-16 bg-slate-100 animate-pulse rounded" />
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
    repair_request: "bg-blue-100 text-blue-700",
    tow_request: "bg-amber-100 text-amber-700",
    emergency: "bg-red-100 text-red-700",
    price_inquiry: "bg-green-100 text-green-700",
    scheduling: "bg-purple-100 text-purple-700",
    general_question: "bg-slate-100 text-slate-700",
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
              <p className="italic text-xs mt-1 bg-slate-50 p-2 rounded">
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
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-slate-50 transition-colors"
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
