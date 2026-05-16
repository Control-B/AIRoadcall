"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, MapPin } from "lucide-react";

type CallerPoint = {
  latitude?: number | null;
  longitude?: number | null;
  label?: string | null;
};

type MechanicPoint = {
  mechanicId: string;
  businessName: string;
  city?: string | null;
  state?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  distanceMiles?: number | null;
};

type GoResultsMapProps = {
  caller: CallerPoint;
  mechanics?: MechanicPoint[];
  className?: string;
};

type CoordinatePoint = { latitude: number; longitude: number };
type CoordinateMechanicPoint = MechanicPoint & CoordinatePoint;

function hasCallerCoordinates(point: CallerPoint): point is CallerPoint & CoordinatePoint {
  return typeof point.latitude === "number" && typeof point.longitude === "number";
}

function hasMechanicCoordinates(point: MechanicPoint): point is CoordinateMechanicPoint {
  return typeof point.latitude === "number" && typeof point.longitude === "number";
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function popupForMechanic(mechanic: MechanicPoint, index: number): string {
  const location = [mechanic.city, mechanic.state].filter(Boolean).join(", ");
  const distance = typeof mechanic.distanceMiles === "number" ? `${mechanic.distanceMiles.toFixed(1)} mi away` : "";
  return [
    `<strong>Option ${index + 1}: ${escapeHtml(mechanic.businessName)}</strong>`,
    escapeHtml(location),
    escapeHtml(distance),
  ]
    .filter(Boolean)
    .join("<br/>");
}

function isConfiguredMapboxToken(token?: string): token is string {
  if (!token) return false;
  const normalized = token.trim().toLowerCase();
  return (
    normalized.startsWith("pk.") &&
    !normalized.includes("placeholder") &&
    !normalized.includes("replace_with") &&
    normalized !== "pk.xxx"
  );
}

export function GoResultsMap({ caller, mechanics = [], className = "h-72 w-full" }: GoResultsMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRefs = useRef<any[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
  const hasConfiguredMapboxToken = isConfiguredMapboxToken(mapboxToken);

  const mechanicMarkers = useMemo(
    () => mechanics.filter(hasMechanicCoordinates),
    [mechanics],
  );
  const callerHasCoordinates = hasCallerCoordinates(caller);
  const hasAnyCoordinates = callerHasCoordinates || mechanicMarkers.length > 0;

  useEffect(() => {
    if (!containerRef.current || !hasConfiguredMapboxToken || !hasAnyCoordinates) return;

    let disposed = false;
    setMapLoaded(false);
    setMapError(null);
    markerRefs.current.forEach((marker) => marker.remove());
    markerRefs.current = [];
    mapRef.current?.remove();
    mapRef.current = null;

    import("mapbox-gl")
      .then((mapboxModule) => {
        if (disposed || !containerRef.current) return;

        const mapboxgl = (mapboxModule as any).default ?? mapboxModule;
        mapboxgl.accessToken = mapboxToken;

        const firstPoint = callerHasCoordinates ? caller : mechanicMarkers[0];
        if (!firstPoint) return;

        const map = new mapboxgl.Map({
          container: containerRef.current,
          style: "mapbox://styles/mapbox/streets-v12",
          center: [firstPoint.longitude, firstPoint.latitude],
          zoom: callerHasCoordinates && mechanicMarkers.length === 0 ? 13 : 10,
          attributionControl: false,
        });

        mapRef.current = map;
        map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
        map.addControl(new mapboxgl.AttributionControl({ compact: true }), "bottom-right");

        const renderMarkers = () => {
          if (disposed) return;
          markerRefs.current.forEach((marker) => marker.remove());
          markerRefs.current = [];

          const bounds = new mapboxgl.LngLatBounds();
          let hasBounds = false;

          if (callerHasCoordinates) {
            const callerMarker = new mapboxgl.Marker({ color: "#f97316" })
              .setLngLat([caller.longitude, caller.latitude])
              .setPopup(
                new mapboxgl.Popup().setHTML(
                  `<strong>Your location</strong><br/>${escapeHtml(caller.label || "GPS location")}`,
                ),
              )
              .addTo(map);
            markerRefs.current.push(callerMarker);
            bounds.extend([caller.longitude, caller.latitude]);
            hasBounds = true;
          }

          mechanicMarkers.forEach((mechanic, index) => {
            const marker = new mapboxgl.Marker({ color: index === 0 ? "#22c55e" : "#2563eb" })
              .setLngLat([mechanic.longitude, mechanic.latitude])
              .setPopup(new mapboxgl.Popup().setHTML(popupForMechanic(mechanic, index)))
              .addTo(map);
            markerRefs.current.push(marker);
            bounds.extend([mechanic.longitude, mechanic.latitude]);
            hasBounds = true;
          });

          if (hasBounds) {
            map.fitBounds(bounds, {
              padding: { top: 56, bottom: 56, left: 42, right: 42 },
              maxZoom: mechanicMarkers.length ? 12 : 14,
              duration: 700,
            });
          }
        };

        map.on("load", () => {
          if (disposed) return;
          map.resize();
          renderMarkers();
          setMapLoaded(true);
          window.requestAnimationFrame(() => map.resize());
        });

        map.on("idle", () => {
          if (!disposed) setMapLoaded(true);
        });

        map.on("error", (event: any) => {
          if (disposed) return;
          const message = event?.error?.message || "Mapbox could not load the map style or tiles.";
          setMapError(message);
        });
      })
      .catch((error) => {
        if (!disposed) {
          setMapError(error?.message || "Mapbox could not start in this browser.");
        }
      });

    return () => {
      disposed = true;
      markerRefs.current.forEach((marker) => marker.remove());
      markerRefs.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [caller, callerHasCoordinates, hasAnyCoordinates, hasConfiguredMapboxToken, mapboxToken, mechanicMarkers]);

  if (!hasConfiguredMapboxToken) {
    return (
      <div className={`${className} flex items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-5 text-center text-sm text-slate-400`}>
        <div>
          <MapPin className="mx-auto mb-2 h-8 w-8 text-orange-400" />
          <p className="font-medium text-slate-200">Mapbox token is not configured.</p>
          <p className="mt-1 text-xs">Set a real `MAPBOX_ACCESS_TOKEN` build-time env var and redeploy.</p>
        </div>
      </div>
    );
  }

  if (!hasAnyCoordinates) {
    return (
      <div className={`${className} flex items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-5 text-center text-sm text-slate-400`}>
        <div>
          <MapPin className="mx-auto mb-2 h-8 w-8 text-orange-400" />
          <p className="font-medium text-slate-200">Map needs GPS coordinates.</p>
          <p className="mt-1 text-xs">Roadcall can still dispatch from your city and state.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-white">Live dispatch map</div>
          <div className="text-xs text-slate-400">
            {mechanicMarkers.length > 0
              ? `${mechanicMarkers.length} nearby option${mechanicMarkers.length === 1 ? "" : "s"} mapped`
              : "Your GPS location is attached"}
          </div>
        </div>
        <div className="rounded-full bg-orange-500/15 px-3 py-1 text-xs font-semibold text-orange-300 ring-1 ring-orange-400/30">
          GPS live
        </div>
      </div>
      <div className="relative min-h-72 bg-slate-950">
        {!mapLoaded && !mapError && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/80 text-sm text-slate-300">
            <Loader2 className="mr-2 h-4 w-4 animate-spin text-orange-400" /> Loading Mapbox map…
          </div>
        )}
        {mapError && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/90 p-5 text-center text-sm text-slate-300">
            <div>
              <MapPin className="mx-auto mb-2 h-8 w-8 text-orange-400" />
              <p className="font-semibold text-white">Mapbox did not load.</p>
              <p className="mt-1 text-xs text-slate-400">{mapError}</p>
            </div>
          </div>
        )}
        <div ref={containerRef} className={`${className} min-h-72`} />
      </div>
    </div>
  );
}
