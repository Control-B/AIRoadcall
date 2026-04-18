"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  CarFront,
  CheckCircle2,
  Clock,
  Loader2,
  Navigation,
  Wrench,
} from "lucide-react";

import { LiveTrackingMap } from "@/components/maps/live-tracking-map";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getMechanicTracking,
  type MechanicTrackingView,
} from "@/lib/api-client";

export default function MechanicTrackingPage() {
  const params = useParams();
  const token = params.token as string;
  const [tracking, setTracking] = useState<MechanicTrackingView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTracking = useCallback(async () => {
    try {
      const data = await getMechanicTracking(token);
      setTracking(data);
      setError("");
    } catch (err: any) {
      setError(err.message || "Unable to load mechanic tracking");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadTracking();
    const interval = setInterval(loadTracking, 5000);
    return () => clearInterval(interval);
  }, [loadTracking]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-6">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-80 w-full rounded-xl" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !tracking) {
    return (
      <div className="mx-auto max-w-xl px-4 py-12">
        <Alert variant="destructive">
          <AlertDescription>
            {error || "This tracking link is invalid or has expired."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const isArrived = tracking.job_status === "mechanic_arrived";
  const StatusIcon = isArrived ? CheckCircle2 : Navigation;

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-6 pb-10">
      <div className="text-center">
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
          Roadcall Mechanic Live Tracking
        </p>
        <h1 className="mt-2 text-3xl font-bold">Job {tracking.public_job_id}</h1>
        <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700">
          <StatusIcon className="h-4 w-4" />
          {isArrived ? "You’ve arrived" : "Live route updates every 5 seconds"}
        </div>
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <LiveTrackingMap
            className="h-[360px] w-full"
            driver={{
              lat: tracking.driver_lat,
              lng: tracking.driver_lng,
              label: tracking.driver_name || "Driver",
              popupHtml: `<strong>${tracking.driver_name || "Driver"}</strong>`,
              color: "#ef4444",
            }}
            mechanic={{
              lat: tracking.mechanic_lat,
              lng: tracking.mechanic_lng,
              label: "You",
              popupHtml: "<strong>You</strong>",
              color: "#2563eb",
            }}
          />
        </CardContent>
      </Card>

      <div className="flex justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-red-500" />
          <span>Driver</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-blue-600" />
          <span>You</span>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Route</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span>ETA: {tracking.eta_minutes ? `~${tracking.eta_minutes} min` : "Unknown"}</span>
            </div>
            <div className="flex items-center gap-2">
              <Navigation className="h-4 w-4 text-muted-foreground" />
              <span>
                Distance: {tracking.distance_miles ? `${tracking.distance_miles.toFixed(1)} mi` : "Unknown"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Wrench className="h-4 w-4 text-muted-foreground" />
              <span className="capitalize">Status: {tracking.job_status.replaceAll("_", " ")}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CarFront className="h-4 w-4" />
              Driver
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="font-semibold">{tracking.driver_name || "Unknown driver"}</p>
            <p className="text-muted-foreground">{tracking.vehicle_type || "Vehicle type unavailable"}</p>
            <p>{tracking.issue_type || "Issue type unavailable"}</p>
            {tracking.issue_summary && (
              <p className="text-muted-foreground">{tracking.issue_summary}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wrench className="h-4 w-4" />
              Dispatch
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="font-semibold">{tracking.mechanic_company || "Roadcall"}</p>
            <p className="text-muted-foreground">{tracking.mechanic_contact || "Mechanic assigned"}</p>
            {tracking.driver_location_captured_at && (
              <p>
                Driver location updated at{" "}
                {new Date(tracking.driver_location_captured_at).toLocaleTimeString()}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {isArrived ? (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>
            Driver and mechanic locations are now aligned. You can begin service.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert>
          <AlertDescription className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            The map refreshes automatically so both you and the driver can follow the route.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}