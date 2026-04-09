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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY || "change-this-to-a-secure-admin-key";

interface Shop {
  id: string;
  business_name: string;
  business_phone: string;
  business_email: string | null;
  business_address: string | null;
  agent_greeting: string;
  sip_phone_number: string | null;
  active: boolean;
  plan: string;
  total_calls_handled: number;
  total_leads_captured: number;
  total_chats_handled: number;
  created_at: string;
}

export default function ShopsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function fetchShops() {
      try {
        const res = await fetch(`${API_BASE}/shops/`, {
          headers: { "x-admin-key": ADMIN_KEY },
        });
        if (res.ok) {
          const data = await res.json();
          setShops(data);
        }
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
    starter: "bg-slate-100 text-slate-700",
    professional: "bg-blue-100 text-blue-700",
    enterprise: "bg-purple-100 text-purple-700",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Shop Customers</h1>
          <p className="text-muted-foreground">
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
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, phone, or address..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Shop List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-16 bg-slate-100 animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <Store className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">
              {shops.length === 0 ? "No shops yet" : "No matching shops"}
            </h3>
            <p className="text-muted-foreground mb-4">
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
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map((shop) => (
            <Link key={shop.id} href={`/admin/shops/${shop.id}`}>
              <Card className="hover:border-blue-200 hover:shadow-md transition-all cursor-pointer">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Store className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">
                            {shop.business_name}
                          </h3>
                          <Badge
                            variant="secondary"
                            className={planColors[shop.plan] || ""}
                          >
                            {shop.plan}
                          </Badge>
                          {!shop.active && (
                            <Badge variant="destructive">Inactive</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            {shop.business_phone}
                          </span>
                          {shop.business_address && (
                            <span className="truncate max-w-xs">
                              {shop.business_address}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right hidden md:block">
                        <div className="text-sm font-medium">
                          {shop.total_calls_handled} calls
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {shop.total_leads_captured} leads
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
