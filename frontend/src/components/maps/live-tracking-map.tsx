"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MapPin } from "lucide-react";
import { loadMapboxCss } from "@/lib/load-mapbox-css";
import { useMapboxToken } from "@/lib/mapbox-token";

type MarkerPoint = {
  lat?: number | null;
  lng?: number | null;
  label: string;
  popupHtml?: string;
  color: string;
};

type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: Record<string, never>;
    geometry: {
      type: "LineString";
      coordinates: number[][];
    };
  }>;
};

interface LiveTrackingMapProps {
  driver: MarkerPoint;
  mechanic: MarkerPoint;
  className?: string;
}

const EMPTY_ROUTE: GeoJsonFeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

export function LiveTrackingMap({
  driver,
  mechanic,
  className = "h-64 sm:h-80 w-full",
}: LiveTrackingMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const driverMarkerRef = useRef<any>(null);
  const mechanicMarkerRef = useRef<any>(null);
  const [routeGeoJson, setRouteGeoJson] = useState<GeoJsonFeatureCollection>(EMPTY_ROUTE);

  const { token: mapboxToken, configured: hasConfiguredMapboxToken, loading: tokenLoading } = useMapboxToken(
    process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN,
  );
  const hasDriverCoords = driver.lat != null && driver.lng != null;
  const hasMechanicCoords = mechanic.lat != null && mechanic.lng != null;
  const routeKey = useMemo(() => {
    if (!hasDriverCoords || !hasMechanicCoords) {
      return null;
    }
    return [mechanic.lng, mechanic.lat, driver.lng, driver.lat].join(",");
  }, [driver.lat, driver.lng, mechanic.lat, mechanic.lng, hasDriverCoords, hasMechanicCoords]);

  useEffect(() => {
    if (!mapContainerRef.current || !hasConfiguredMapboxToken) return;

    let mapInstance: any;
    let mounted = true;

    loadMapboxCss();
    import("mapbox-gl").then((mapboxModule) => {
      if (!mounted || !mapContainerRef.current) return;
      const mapboxgl = (mapboxModule as any).default ?? mapboxModule;
      mapboxgl.accessToken = mapboxToken;

      mapInstance = new mapboxgl.Map({
        container: mapContainerRef.current,
        style: "mapbox://styles/mapbox/streets-v12",
        center: [-96, 37.8],
        zoom: 3,
      });

      mapInstance.addControl(new mapboxgl.NavigationControl(), "top-right");
      mapRef.current = mapInstance;
    });

    return () => {
      mounted = false;
      if (mapInstance) {
        mapInstance.remove();
      }
      mapRef.current = null;
      driverMarkerRef.current = null;
      mechanicMarkerRef.current = null;
    };
  }, [hasConfiguredMapboxToken, mapboxToken]);

  useEffect(() => {
    if (!routeKey || !hasConfiguredMapboxToken) {
      setRouteGeoJson(EMPTY_ROUTE);
      return;
    }

    let cancelled = false;

    async function loadRoute() {
      try {
        const response = await fetch(
          `https://api.mapbox.com/directions/v5/mapbox/driving/${routeKey}?geometries=geojson&overview=full&access_token=${mapboxToken}`
        );
        if (!response.ok) {
          throw new Error("Unable to load route");
        }
        const data = await response.json();
        const coordinates = data?.routes?.[0]?.geometry?.coordinates;
        if (!cancelled && Array.isArray(coordinates)) {
          setRouteGeoJson({
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                properties: {},
                geometry: {
                  type: "LineString",
                  coordinates,
                },
              },
            ],
          });
        }
      } catch {
        if (!cancelled) {
          setRouteGeoJson(EMPTY_ROUTE);
        }
      }
    }

    loadRoute();

    return () => {
      cancelled = true;
    };
  }, [routeKey, hasConfiguredMapboxToken, mapboxToken]);

  useEffect(() => {
    if (!hasConfiguredMapboxToken) return;

    let cancelled = false;

    async function syncMap() {
      const map = mapRef.current;
      if (!map) return;

      const mapboxModule = await import("mapbox-gl");
      if (cancelled) return;
      const mapboxgl = (mapboxModule as any).default ?? mapboxModule;

      const render = () => {
        if (!map.getSource("live-route-source")) {
          map.addSource("live-route-source", {
            type: "geojson",
            data: routeGeoJson,
          });
          map.addLayer({
            id: "live-route-line",
            type: "line",
            source: "live-route-source",
            layout: {
              "line-join": "round",
              "line-cap": "round",
            },
            paint: {
              "line-color": "#2563eb",
              "line-width": 5,
              "line-opacity": 0.7,
            },
          });
        } else {
          const source = map.getSource("live-route-source");
          source?.setData(routeGeoJson);
        }

        if (hasDriverCoords) {
          if (driverMarkerRef.current) {
            driverMarkerRef.current.setLngLat([driver.lng!, driver.lat!]);
          } else {
            const el = document.createElement("div");
            el.innerHTML = `<div style="background:${driver.color};width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>`;
            driverMarkerRef.current = new mapboxgl.Marker(el)
              .setLngLat([driver.lng!, driver.lat!])
              .setPopup(
                new mapboxgl.Popup().setHTML(driver.popupHtml || `<strong>${driver.label}</strong>`)
              )
              .addTo(map);
          }
        }

        if (hasMechanicCoords) {
          if (mechanicMarkerRef.current) {
            mechanicMarkerRef.current.setLngLat([mechanic.lng!, mechanic.lat!]);
          } else {
            const el = document.createElement("div");
            el.innerHTML = `<div style="background:${mechanic.color};width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>`;
            mechanicMarkerRef.current = new mapboxgl.Marker(el)
              .setLngLat([mechanic.lng!, mechanic.lat!])
              .setPopup(
                new mapboxgl.Popup().setHTML(mechanic.popupHtml || `<strong>${mechanic.label}</strong>`)
              )
              .addTo(map);
          }
        }

        const bounds = new mapboxgl.LngLatBounds();
        let hasBounds = false;

        if (hasDriverCoords) {
          bounds.extend([driver.lng!, driver.lat!]);
          hasBounds = true;
        }

        if (hasMechanicCoords) {
          bounds.extend([mechanic.lng!, mechanic.lat!]);
          hasBounds = true;
        }

        routeGeoJson.features[0]?.geometry.coordinates.forEach((coordinate) => {
          bounds.extend([coordinate[0], coordinate[1]]);
          hasBounds = true;
        });

        if (hasBounds) {
          map.fitBounds(bounds, { padding: 60, maxZoom: 15, duration: 800 });
        }
      };

      if (map.isStyleLoaded()) {
        render();
      } else {
        map.once("load", render);
      }
    }

    syncMap();

    return () => {
      cancelled = true;
    };
  }, [driver, mechanic, routeGeoJson, hasConfiguredMapboxToken, hasDriverCoords, hasMechanicCoords]);

  if (!hasConfiguredMapboxToken) {
    return (
      <div className={`${className} flex items-center justify-center bg-muted`}>
        <div className="text-center text-sm text-muted-foreground">
          <MapPin className="mx-auto mb-2 h-8 w-8" />
          <p>{tokenLoading ? "Loading map configuration…" : "Map configuration is not ready"}</p>
          {hasDriverCoords && (
            <p className="mt-2">
              {driver.label}: {driver.lat!.toFixed(4)}, {driver.lng!.toFixed(4)}
            </p>
          )}
          {hasMechanicCoords && (
            <p>
              {mechanic.label}: {mechanic.lat!.toFixed(4)}, {mechanic.lng!.toFixed(4)}
            </p>
          )}
        </div>
      </div>
    );
  }

  return <div ref={mapContainerRef} className={className} />;
}