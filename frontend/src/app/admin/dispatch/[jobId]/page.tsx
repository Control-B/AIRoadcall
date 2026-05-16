"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  User,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { LiveTrackingMap } from "@/components/maps/live-tracking-map";
import {
  getAdminMechanicTracking,
  isAuthenticated,
  type AdminMechanicTrackingView,
} from "@/lib/admin-auth";

export default function AdminDispatchTrackingPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const [tracking, setTracking] = useState<AdminMechanicTrackingView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  const loadTracking = useCallback(async () => {
    try {
      const data = await getAdminMechanicTracking(jobId);
      setTracking(data);
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to load mechanic tracking");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (!isAuthenticated()) {
      window.location.href = "/admin/login";
      return;
    }
    loadTracking();
    const interval = setInterval(loadTracking, 5000);
    return () => clearInterval(interval);
  }, [loadTracking]);

  async function copyDriverCoords() {
    if (!tracking?.driver_lat || !tracking?.driver_lng) return;
    await navigator.clipboard.writeText(`${tracking.driver_lat}, ${tracking.driver_lng}`);
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded bg-slate-100 animate-pulse" />
          <div className="h-8 w-72 rounded bg-slate-100 animate-pulse" />
        </div>
        <div className="h-80 rounded-xl bg-slate-100 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/admin">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Mechanic Tracking</h1>
            <p className="text-sm text-muted-foreground">
              Job {tracking?.public_job_id || jobId}
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={loadTracking}>
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Tracking error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <LiveTrackingMap
              className="h-[480px] w-full"
              driver={{
                lat: tracking?.driver_lat,
                lng: tracking?.driver_lng,
                label: "Caller",
                popupHtml: `<strong>Caller</strong><br/>${tracking?.driver_name || "Unknown"}`,
                color: "#ef4444",
              }}
              mechanic={{
                lat: tracking?.mechanic_lat,
                lng: tracking?.mechanic_lng,
                label: tracking?.mechanic_company || "Mechanic",
                popupHtml: `<strong>${tracking?.mechanic_company || "Mechanic"}</strong><br/>${tracking?.mechanic_contact || ""}`,
                color: "#2563eb",
              }}
            />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Dispatch Snapshot</CardTitle>
              <CardDescription>Live route and ETA updates every 5 seconds</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Status</p>
                  <p className="font-semibold capitalize">{tracking?.job_status?.replaceAll("_", " ")}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">ETA</p>
                  <p className="font-semibold">{tracking?.eta_minutes ? `~${tracking.eta_minutes} min` : "Unknown"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Distance</p>
                  <p className="font-semibold">{tracking?.distance_miles ? `${tracking.distance_miles.toFixed(1)} mi` : "Unknown"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Location captured</p>
                  <p className="font-semibold">{tracking?.driver_location_captured_at ? new Date(tracking.driver_location_captured_at).toLocaleTimeString() : "Pending"}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><User className="h-4 w-4" /> Driver</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p><span className="text-muted-foreground">Name:</span> <span className="font-medium">{tracking?.driver_name || "Unknown"}</span></p>
              <p><span className="text-muted-foreground">Vehicle:</span> <span className="font-medium">{tracking?.vehicle_type || "Unknown"}</span></p>
              <p><span className="text-muted-foreground">Issue:</span> <span className="font-medium">{tracking?.issue_type || "Unknown"}</span></p>
              {tracking?.issue_summary && (
                <p><span className="text-muted-foreground">Summary:</span> <span className="font-medium">{tracking.issue_summary}</span></p>
              )}
              {tracking?.driver_lat && tracking?.driver_lng && (
                <div className="space-y-2">
                  <p><span className="text-muted-foreground">GPS:</span> <span className="font-medium">{tracking.driver_lat.toFixed(5)}, {tracking.driver_lng.toFixed(5)}</span></p>
                  <Button variant="outline" size="sm" onClick={copyDriverCoords}>Copy driver coordinates</Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Wrench className="h-4 w-4" /> Mechanic</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p><span className="text-muted-foreground">Company:</span> <span className="font-medium">{tracking?.mechanic_company || "Unassigned"}</span></p>
              <p><span className="text-muted-foreground">Contact:</span> <span className="font-medium">{tracking?.mechanic_contact || "Unknown"}</span></p>
              {tracking?.mechanic_lat && tracking?.mechanic_lng && (
                <p><span className="text-muted-foreground">GPS:</span> <span className="font-medium">{tracking.mechanic_lat.toFixed(5)}, {tracking.mechanic_lng.toFixed(5)}</span></p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}