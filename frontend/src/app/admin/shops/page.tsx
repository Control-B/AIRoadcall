"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus,
  Store,
  Phone,
  ChevronRight,
  Search,
  Filter,
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

interface Shop {
  id: string;
  business_name: string;
  business_phone: string;
  business_email: string | null;
  business_address: string | null;
  agent_greeting: string;
  sip_phone_number: string | null;
  phone_onboarding_mode: string;
  twilio_number_status: string;
  appointment_booking_enabled: boolean;
  calcom_calendar_url: string | null;
  active: boolean;
  plan: string;
  total_calls_handled: number;
  total_leads_captured: number;
  total_chats_handled: number;
  appointments_booked: number;
  revenue_opportunities_cents: number;
  created_at: string;
}

export default function ShopsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function fetchShops() {
      try {
        const data = await adminFetch<Shop[]>("/shops/");
        setShops(data);
      } catch (err) {
        console.error("Failed to fetch shops:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchShops();
  }, []);

  const filtered = shops.filter(
    (s) =>
      s.business_name.toLowerCase().includes(search.toLowerCase()) ||
      s.business_phone.includes(search) ||
      (s.business_address || "").toLowerCase().includes(search.toLowerCase())
  );

  const planColors: Record<string, string> = {
    standard: "bg-slate-500/20 text-slate-300",
    professional: "bg-blue-500/20 text-blue-300",
    advanced: "bg-purple-500/20 text-purple-300",
    widget_only: "bg-cyan-500/20 text-cyan-300",
    ai_telephony: "bg-emerald-500/20 text-emerald-300",
    widget_voice: "bg-orange-500/20 text-orange-300",
    enterprise: "bg-indigo-500/20 text-indigo-300",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Shop Customers</h1>
          <p className="text-slate-400">
            Manage shops subscribed to AI Receptionist
          </p>
        </div>
        <Link href="/admin/shops/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Add Shop
          </Button>
        </Link>
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <Input
            placeholder="Search by name, phone, or address..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-white/5 border-white/10 text-slate-200 placeholder:text-slate-500"
          />
        </div>
      </div>

      {/* Shop List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl border border-white/5 bg-slate-900/60" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 py-16 text-center">
          <Store className="h-12 w-12 text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2 text-slate-200">
            {shops.length === 0 ? "No shops yet" : "No matching shops"}
          </h3>
          <p className="text-slate-400 mb-4">
            {shops.length === 0
              ? "Add your first shop customer to get started."
              : "Try a different search term."}
          </p>
          {shops.length === 0 && (
            <Link href="/admin/shops/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add First Shop
              </Button>
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((shop) => (
            <Link key={shop.id} href={`/admin/shops/${shop.id}`}>
              <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-4 hover:border-blue-500/30 hover:bg-slate-900 transition-all cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                      <Store className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-slate-100">{shop.business_name}</h3>
                        <Badge variant="secondary" className={planColors[shop.plan] || ""}>{shop.plan}</Badge>
                        {!shop.active && <Badge variant="destructive">Inactive</Badge>}
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-slate-400">
                        <span className="flex items-center gap-1">
                          <Phone className="h-3 w-3" />
                          {shop.business_phone}
                        </span>
                        {shop.business_address && (
                          <span className="truncate max-w-xs">{shop.business_address}</span>
                        )}
                        {shop.appointment_booking_enabled && (
                          <span className="text-blue-300">Calendar enabled</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right hidden md:block">
                      <div className="text-sm font-medium text-slate-200">{shop.total_calls_handled} calls</div>
                      <div className="text-xs text-slate-500">{shop.total_leads_captured} leads · {shop.appointments_booked || 0} appts</div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-slate-500" />
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
