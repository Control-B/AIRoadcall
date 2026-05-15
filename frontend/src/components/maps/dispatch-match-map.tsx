"use client";

import { useEffect, useMemo, useRef } from "react";

import type { DispatchMatchResponse } from "@/lib/api-client";

type DispatchMatchMapProps = {
  match: DispatchMatchResponse;
  className?: string;
};

export function DispatchMatchMap({ match, className = "h-[420px] w-full" }: DispatchMatchMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRefs = useRef<any[]>([]);
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

  const routeGeoJson = useMemo(() => {
    return {
      type: "FeatureCollection",
      features: (match.map_routes || [])
        .filter((route) => route.geometry?.coordinates?.length)
        .map((route) => ({
          type: "Feature",
          properties: { provider_id: route.provider_id },
          geometry: route.geometry,
        })),
    } as GeoJSON.FeatureCollection;
  }, [match.map_routes]);

  useEffect(() => {
    if (!containerRef.current || !mapboxToken || !match.coordinates) return;

    let disposed = false;
    import("mapbox-gl").then((mapboxgl) => {
      if (disposed || !containerRef.current) return;
      (mapboxgl as any).accessToken = mapboxToken;

      const map = new mapboxgl.Map({
        container: containerRef.current,
        style: "mapbox://styles/mapbox/streets-v12",
        center: [match.coordinates!.longitude, match.coordinates!.latitude],
        zoom: 9,
      });
      map.addControl(new mapboxgl.NavigationControl(), "top-right");
      mapRef.current = map;
    });

    return () => {
      disposed = true;
      markerRefs.current.forEach((marker) => marker.remove());
      markerRefs.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [mapboxToken, match.coordinates]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !match.coordinates) return;

    let cancelled = false;
    import("mapbox-gl").then((mapboxgl) => {
      const renderMapData = () => {
        if (cancelled) return;
        markerRefs.current.forEach((marker) => marker.remove());
        markerRefs.current = [];

        const bounds = new mapboxgl.LngLatBounds();
        const caller = match.coordinates!;
        const callerMarker = new mapboxgl.Marker({ color: "#ef4444" })
          .setLngLat([caller.longitude, caller.latitude])
          .setPopup(new mapboxgl.Popup().setHTML(`<strong>Caller</strong><br/>${match.normalized_location || "Location"}`))
          .addTo(map);
        markerRefs.current.push(callerMarker);
        bounds.extend([caller.longitude, caller.latitude]);

        match.providers.forEach((provider, index) => {
          const marker = new mapboxgl.Marker({ color: index === 0 ? "#22c55e" : "#2563eb" })
            .setLngLat([provider.longitude, provider.latitude])
            .setPopup(
              new mapboxgl.Popup().setHTML(
                `<strong>${provider.business_name}</strong><br/>${provider.city || ""} ${provider.state || ""}<br/>${provider.estimated_drive_minutes ?? "?"} min ETA · ${provider.distance_miles.toFixed(1)} mi`
              )
            )
            .addTo(map);
          markerRefs.current.push(marker);
          bounds.extend([provider.longitude, provider.latitude]);
        });

        if (!map.getSource("dispatch-routes")) {
          map.addSource("dispatch-routes", { type: "geojson", data: routeGeoJson });
          map.addLayer({
            id: "dispatch-routes-line",
            type: "line",
            source: "dispatch-routes",
            paint: {
              "line-color": "#f97316",
              "line-width": 3,
              "line-opacity": 0.75,
            },
          });
        } else {
          (map.getSource("dispatch-routes") as any).setData(routeGeoJson);
        }

        if (!bounds.isEmpty()) {
          map.fitBounds(bounds, { padding: 64, maxZoom: 12 });
        }
      };

      if (map.isStyleLoaded()) renderMapData();
      else map.once("load", renderMapData);
    });

    return () => {
      cancelled = true;
    };
  }, [match, routeGeoJson]);

  if (!mapboxToken) {
    return (
      <div className={`${className} flex items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500`}>
        Map requires `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN`.
      </div>
    );
  }

  if (!match.coordinates) {
    return (
      <div className={`${className} flex items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500`}>
        No caller coordinates available.
      </div>
    );
  }

  return <div ref={containerRef} className={`${className} overflow-hidden rounded-xl border border-slate-200`} />;
}
