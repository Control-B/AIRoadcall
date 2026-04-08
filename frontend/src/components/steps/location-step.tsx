"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { updateDriverLocation } from "@/lib/api-client";
import {
  MapPin,
  Loader2,
  CheckCircle2,
  XCircle,
  Navigation,
} from "lucide-react";

interface LocationStepProps {
  token: string;
  onSuccess: (lat: number, lng: number) => void;
}

type LocationState = "idle" | "requesting" | "success" | "error";

export function LocationStep({ token, onSuccess }: LocationStepProps) {
  const [state, setState] = useState<LocationState>("idle");
  const [error, setError] = useState<string>("");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const mapContainerRef = useRef<HTMLDivElement>(null);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setState("error");
      setError("Geolocation is not supported by your browser");
      return;
    }

    setState("requesting");
    setError("");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCoords({ lat: latitude, lng: longitude });
        setState("success");
      },
      (err) => {
        setState("error");
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setError(
              "Location permission denied. Please enable location access in your browser settings and try again."
            );
            break;
          case err.POSITION_UNAVAILABLE:
            setError(
              "Unable to determine your location. Please make sure GPS is enabled."
            );
            break;
          case err.TIMEOUT:
            setError(
              "Location request timed out. Please try again."
            );
            break;
          default:
            setError("An unexpected error occurred while getting your location.");
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      }
    );
  }, []);

  const submitLocation = useCallback(async () => {
    if (!coords) return;

    setSubmitting(true);
    try {
      await updateDriverLocation(token, coords.lat, coords.lng);
      onSuccess(coords.lat, coords.lng);
    } catch (err) {
      setError("Failed to save your location. Please try again.");
      setState("error");
    } finally {
      setSubmitting(false);
    }
  }, [coords, token, onSuccess]);

  // Initialize Mapbox map when coordinates are available
  useEffect(() => {
    if (!coords || !mapContainerRef.current) return;

    const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
    if (!mapboxToken) return;

    let map: any;

    import("mapbox-gl").then((mapboxgl) => {
      (mapboxgl as any).accessToken = mapboxToken;

      map = new mapboxgl.Map({
        container: mapContainerRef.current!,
        style: "mapbox://styles/mapbox/streets-v12",
        center: [coords.lng, coords.lat],
        zoom: 15,
        interactive: false,
      });

      new mapboxgl.Marker({ color: "#ef4444" })
        .setLngLat([coords.lng, coords.lat])
        .addTo(map);
    });

    return () => {
      if (map) map.remove();
    };
  }, [coords]);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
          <Navigation className="h-8 w-8 text-blue-600" />
        </div>
        <h2 className="text-2xl font-bold">Confirm Your Location</h2>
        <p className="mt-2 text-muted-foreground">
          We need your precise location to send help to the right spot
        </p>
      </div>

      {state === "idle" && (
        <Card>
          <CardContent className="pt-6">
            <Button
              size="xl"
              className="w-full"
              onClick={requestLocation}
            >
              <MapPin className="mr-2 h-5 w-5" />
              Enable Location Access
            </Button>
            <p className="mt-3 text-center text-xs text-muted-foreground">
              Your browser will ask for permission to access your location
            </p>
          </CardContent>
        </Card>
      )}

      {state === "requesting" && (
        <Card>
          <CardContent className="flex flex-col items-center py-10">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="font-medium">Getting your location...</p>
            <p className="text-sm text-muted-foreground mt-1">
              Please allow location access when prompted
            </p>
          </CardContent>
        </Card>
      )}

      {state === "error" && (
        <div className="space-y-4">
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertTitle>Location Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button
            size="lg"
            variant="outline"
            className="w-full"
            onClick={requestLocation}
          >
            Try Again
          </Button>
        </div>
      )}

      {state === "success" && coords && (
        <div className="space-y-4">
          <Alert variant="success">
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle>Location Found</AlertTitle>
            <AlertDescription>
              Your location has been captured successfully
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Your Location</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                ref={mapContainerRef}
                className="h-48 w-full rounded-lg overflow-hidden bg-muted"
              >
                {!process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN && (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center text-sm text-muted-foreground">
                      <MapPin className="h-8 w-8 mx-auto mb-2 text-red-500" />
                      <p>
                        📍 {coords.lat.toFixed(5)}, {coords.lng.toFixed(5)}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Button
            size="xl"
            className="w-full"
            onClick={submitLocation}
            disabled={submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Saving Location...
              </>
            ) : (
              "Continue to Payment"
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
