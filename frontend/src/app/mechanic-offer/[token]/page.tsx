"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  getMechanicOffer,
  getMechanicOfferStatus,
  respondMechanicOffer,
  type MechanicOfferView,
} from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, MapPin, CheckCircle2, XCircle, Ban } from "lucide-react";
import { formatIssueType } from "@/lib/utils";

export default function MechanicOfferPage() {
  const params = useParams();
  const token = params.token as string;
  const mapRef = useRef<HTMLDivElement>(null);

  const [offer, setOffer] = useState<MechanicOfferView | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pollState, setPollState] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getMechanicOffer(token);
      setOffer(data);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not load this offer.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!offer?.driver_lat || !offer?.driver_lng || !mapRef.current) return;
    const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
    if (!mapboxToken) return;

    let map: import("mapbox-gl").Map | undefined;
    import("mapbox-gl").then((mapboxgl) => {
      (mapboxgl as unknown as { accessToken: string }).accessToken = mapboxToken;
      map = new mapboxgl.Map({
        container: mapRef.current!,
        style: "mapbox://styles/mapbox/streets-v12",
        center: [offer.driver_lng!, offer.driver_lat!],
        zoom: 12,
      });
      new mapboxgl.Marker({ color: "#ef4444" })
        .setLngLat([offer.driver_lng!, offer.driver_lat!])
        .addTo(map);
    });
    return () => {
      map?.remove();
    };
  }, [offer?.driver_lat, offer?.driver_lng]);

  useEffect(() => {
    if (!offer || offer.offer_state !== "active" || offer.job_filled) return;
    const t = setInterval(async () => {
      try {
        const s = await getMechanicOfferStatus(token);
        setPollState(s.offer_state);
        if (s.offer_state === "superseded" || s.job_filled) {
          await load();
        }
      } catch {
        /* ignore */
      }
    }, 4000);
    return () => clearInterval(t);
  }, [offer, token, load]);

  const onRespond = async (response: "accepted" | "declined") => {
    setSubmitting(true);
    try {
      await respondMechanicOffer(token, {
        response,
        eta_minutes: response === "accepted" ? 25 : undefined,
      });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not submit response.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  if (error && !offer) {
    return (
      <div className="mx-auto max-w-md p-6 pt-12 text-center">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!offer) return null;

  const closed =
    offer.offer_state === "closed" ||
    offer.offer_state === "superseded" ||
    offer.offer_state === "filled" ||
    pollState === "superseded" ||
    pollState === "filled";

  return (
    <div className="mx-auto max-w-lg px-4 py-8 pb-16">
      <p className="text-center text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Roadcall dispatch
      </p>
      <p className="text-center text-sm text-muted-foreground">{offer.public_job_id}</p>

      {error ? (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {offer.job_filled && offer.offer_state === "filled" ? (
        <Alert className="mt-6">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>
            Another provider already accepted this job. You do not need to do anything else.
          </AlertDescription>
        </Alert>
      ) : null}

      {offer.offer_state === "superseded" || pollState === "superseded" ? (
        <Alert className="mt-6">
          <Ban className="h-4 w-4" />
          <AlertDescription>
            This offer is no longer active — another provider accepted first.
          </AlertDescription>
        </Alert>
      ) : null}

      {!closed ? (
        <>
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-lg">Work order</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <span className="text-muted-foreground">Issue: </span>
                {formatIssueType(offer.issue_type)}
              </p>
              {offer.issue_summary ? <p>{offer.issue_summary}</p> : null}
              {offer.vehicle_type ? (
                <p>
                  <span className="text-muted-foreground">Vehicle: </span>
                  {offer.vehicle_type}
                </p>
              ) : null}
              {offer.driver_area ? (
                <p>
                  <span className="text-muted-foreground">Area: </span>
                  {offer.driver_area}
                </p>
              ) : null}
            </CardContent>
          </Card>

          <div className="mt-4 overflow-hidden rounded-xl border bg-muted">
            <div ref={mapRef} className="h-56 w-full" />
            {!process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN ? (
              <div className="flex h-56 items-center justify-center px-4 text-center text-xs text-muted-foreground">
                <MapPin className="mr-2 h-5 w-5 shrink-0" />
                Map preview needs NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN
              </div>
            ) : null}
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <button
              type="button"
              disabled={submitting}
              onClick={() => onRespond("accepted")}
              className="flex items-center justify-center gap-2 rounded-xl bg-green-600 px-4 py-3 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
              Accept
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => onRespond("declined")}
              className="flex items-center justify-center gap-2 rounded-xl border border-destructive/50 bg-background px-4 py-3 text-sm font-semibold text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              <XCircle className="h-4 w-4" />
              Decline
            </button>
          </div>
        </>
      ) : null}

      {offer.offer_state === "closed" && offer.dispatch_status === "accepted" ? (
        <Alert className="mt-6" variant="default">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>Thank you — your acceptance is recorded.</AlertDescription>
        </Alert>
      ) : null}

      {(offer.offer_state === "closed" && offer.dispatch_status === "declined") ||
      offer.dispatch_status === "declined" ? (
        <Alert className="mt-6">
          <AlertDescription>Decline recorded. Thank you for responding.</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
