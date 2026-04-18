"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { getTracking, type TrackingView } from "@/lib/api-client";
import { LiveTrackingMap } from "@/components/maps/live-tracking-map";
import {
  Wrench,
  Clock,
  CheckCircle2,
  Navigation,
  Loader2,
} from "lucide-react";

interface TrackingStepProps {
  token: string;
  mechanicCompany?: string;
  mechanicContact?: string;
}

export function TrackingStep({
  token,
  mechanicCompany,
  mechanicContact,
}: TrackingStepProps) {
  const [tracking, setTracking] = useState<TrackingView | null>(null);
  const [loading, setLoading] = useState(true);

  const pollTracking = useCallback(async () => {
    try {
      const data = await getTracking(token);
      setTracking(data);
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    pollTracking();
    const interval = setInterval(pollTracking, 5000);
    return () => clearInterval(interval);
  }, [pollTracking]);

  const statusLabel =
    tracking?.job_status === "mechanic_arrived"
      ? "Mechanic Has Arrived!"
      : tracking?.job_status === "mechanic_en_route"
      ? "Mechanic En Route"
      : "Tracking";

  const StatusIcon =
    tracking?.job_status === "mechanic_arrived" ? CheckCircle2 : Navigation;

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48 mx-auto" />
        <Skeleton className="h-64 w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div
          className={`mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full ${
            tracking?.job_status === "mechanic_arrived"
              ? "bg-green-100"
              : "bg-blue-100"
          }`}
        >
          <StatusIcon
            className={`h-8 w-8 ${
              tracking?.job_status === "mechanic_arrived"
                ? "text-green-600"
                : "text-blue-600"
            }`}
          />
        </div>
        <h2 className="text-2xl font-bold">{statusLabel}</h2>
        {tracking?.eta_minutes && (
          <p className="mt-1 text-lg font-semibold text-primary">
            ETA: ~{tracking.eta_minutes} minutes
          </p>
        )}
        {tracking?.distance_miles && (
          <p className="mt-1 text-sm text-muted-foreground">
            Distance: {tracking.distance_miles.toFixed(1)} miles away
          </p>
        )}
      </div>

      {/* Map */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <LiveTrackingMap
            driver={{
              lat: tracking?.driver_lat,
              lng: tracking?.driver_lng,
              label: "You",
              popupHtml: "<strong>You</strong>",
              color: "#ef4444",
            }}
            mechanic={{
              lat: tracking?.mechanic_lat,
              lng: tracking?.mechanic_lng,
              label: tracking?.mechanic_company || "Mechanic",
              popupHtml: `<strong>${tracking?.mechanic_company || "Mechanic"}</strong>`,
              color: "#2563eb",
            }}
          />
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-red-500" />
          <span>You</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-blue-600" />
          <span>Mechanic</span>
        </div>
      </div>

      {/* Mechanic Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your Mechanic</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
              <Wrench className="h-6 w-6 text-blue-600" />
            </div>
            <div className="flex-1">
              <p className="font-semibold">
                {tracking?.mechanic_company || mechanicCompany || "Assigned Mechanic"}
              </p>
              <p className="text-sm text-muted-foreground">
                {tracking?.mechanic_contact || mechanicContact}
              </p>
              {(tracking?.mechanic_address || tracking?.mechanic_city || tracking?.mechanic_state) && (
                <p className="text-sm text-muted-foreground">
                  {[tracking?.mechanic_address, tracking?.mechanic_city, tracking?.mechanic_state]
                    .filter(Boolean)
                    .join(", ")}
                </p>
              )}
            </div>
            {tracking?.mechanic_last_updated && (
              <div className="text-right">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>
                    Updated{" "}
                    {new Date(tracking.mechanic_last_updated).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {tracking?.job_status === "mechanic_arrived" ? (
        <Alert variant="success">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>
            Your mechanic has arrived! They should be approaching your vehicle
            now.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert>
          <AlertDescription className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Live tracking updates every 5 seconds
          </AlertDescription>
        </Alert>
      )}

      {!tracking?.mechanic_lat && tracking?.tracking_status !== "arrived" && (
        <Alert variant="warning">
          <AlertDescription>
            Mechanic location is not yet available. They may still be preparing
            to depart. Tracking will update automatically.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
