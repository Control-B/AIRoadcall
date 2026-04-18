"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  getRematchCandidates,
  selectRematchMechanic,
  type RematchCandidate,
  type JobDriverView,
} from "@/lib/api-client";
import { Loader2, MapPin, Send } from "lucide-react";

interface RematchStepProps {
  token: string;
  onOfferSent: (job: JobDriverView) => void;
}

export function RematchStep({ token, onOfferSent }: RematchStepProps) {
  const [candidates, setCandidates] = useState<RematchCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sendingId, setSendingId] = useState<string | null>(null);
  const mapRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getRematchCandidates(token, 20);
      setCandidates(data);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not load nearby providers.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!candidates.length || !mapRef.current) return;
    const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
    if (!mapboxToken) {
      return;
    }

    const lats = candidates.map((c) => c.base_lat);
    const lngs = candidates.map((c) => c.base_lng);
    const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
    const centerLng = lngs.reduce((a, b) => a + b, 0) / lngs.length;

    let map: import("mapbox-gl").Map | undefined;
    import("mapbox-gl").then((mapboxgl) => {
      (mapboxgl as unknown as { accessToken: string }).accessToken = mapboxToken;
      map = new mapboxgl.Map({
        container: mapRef.current!,
        style: "mapbox://styles/mapbox/streets-v12",
        center: [centerLng, centerLat],
        zoom: 9,
      });
      map.addControl(new mapboxgl.NavigationControl(), "top-right");
      candidates.forEach((c, i) => {
        const color = `hsl(${(i * 47) % 360} 70% 45%)`;
        new mapboxgl.Marker({ color })
          .setLngLat([c.base_lng, c.base_lat])
          .setPopup(new mapboxgl.Popup().setHTML(`<strong>${c.company_name}</strong>`))
          .addTo(map!);
      });
    });
    return () => {
      map?.remove();
    };
  }, [candidates]);

  const sendTo = async (mechanicId: string) => {
    setSendingId(mechanicId);
    try {
      const job = await selectRematchMechanic(token, mechanicId);
      onOfferSent(job);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not send request.");
    } finally {
      setSendingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold">Choose another provider</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Nearby shops ranked for your location. Tap to send them the same dispatch link style offer.
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {candidates.length === 0 ? (
        <Alert>
          <AlertDescription>
            No additional providers are available right now. Please call support.
          </AlertDescription>
        </Alert>
      ) : null}

      {process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN ? (
        <div className="overflow-hidden rounded-xl border bg-muted">
          <div ref={mapRef} className="h-48 w-full" />
        </div>
      ) : (
        <div className="flex h-12 items-center justify-center rounded-xl border border-dashed text-xs text-muted-foreground">
          <MapPin className="mr-2 h-4 w-4" />
          Map preview needs NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN
        </div>
      )}

      <div className="space-y-3">
        {candidates.map((c) => (
          <Card key={c.mechanic_id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{c.company_name}</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-3">
              <div className="text-sm text-muted-foreground">
                {[c.city, c.state].filter(Boolean).join(", ")}
                {c.distance_miles != null ? (
                  <span className="ml-2">~{c.distance_miles.toFixed(1)} mi</span>
                ) : null}
                {c.rating != null ? (
                  <span className="ml-2">Rating {c.rating.toFixed(1)}</span>
                ) : null}
              </div>
              <button
                type="button"
                disabled={!!sendingId}
                onClick={() => sendTo(c.mechanic_id)}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {sendingId === c.mechanic_id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Offer job
              </button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
