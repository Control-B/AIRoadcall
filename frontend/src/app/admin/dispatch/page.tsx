"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, MapPin, Phone, Search } from "lucide-react";

import { DispatchMatchMap } from "@/components/maps/dispatch-match-map";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  DispatchMatchResponse,
  matchProvidersByLocation,
} from "@/lib/api-client";
import { getToken as getAdminToken, isAuthenticated as isAdminAuthenticated } from "@/lib/admin-auth";

export default function AdminDispatchMatchPage() {
  const [locationText, setLocationText] = useState("Saint Petersburg, FL");
  const [serviceNeeded, setServiceNeeded] = useState("mobile roadside repair");
  const [vehicleType, setVehicleType] = useState("heavy-duty truck");
  const [match, setMatch] = useState<DispatchMatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAdminAuthenticated()) {
      window.location.href = "/admin/login";
    }
  }, []);

  async function runMatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getAdminToken();
    if (!token) {
      window.location.href = "/admin/login";
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await matchProvidersByLocation(
        {
          location_text: locationText,
          service_needed: serviceNeeded,
          vehicle_type: vehicleType || undefined,
          urgency: "roadside",
          limit: 5,
        },
        token
      );
      setMatch(response);
    } catch (err: any) {
      setError(err.message || "Unable to match providers");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/admin">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Dispatch Matching</h1>
          <p className="text-sm text-muted-foreground">
            Geocode caller text, rank nearby providers, and preview the dispatch map.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" /> Match by location
          </CardTitle>
          <CardDescription>
            Provider names, distance, and ETA come only from the backend match response.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={runMatch} className="grid gap-4 lg:grid-cols-[1.4fr_1fr_1fr_auto]">
            <Input
              value={locationText}
              onChange={(event) => setLocationText(event.target.value)}
              placeholder="Caller location, highway, truck stop, city/state"
              required
            />
            <Input
              value={serviceNeeded}
              onChange={(event) => setServiceNeeded(event.target.value)}
              placeholder="Service needed"
              required
            />
            <Input
              value={vehicleType}
              onChange={(event) => setVehicleType(event.target.value)}
              placeholder="Vehicle type"
            />
            <Button type="submit" disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              Match
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Match failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {match && (
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.9fr]">
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" /> Live dispatch map
              </CardTitle>
              <CardDescription>
                {match.normalized_location || match.message}
                {match.search_radius_miles ? ` · searched ${match.search_radius_miles} miles` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DispatchMatchMap match={match} className="h-[560px] w-full" />
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Alert>
              <AlertTitle className="capitalize">{match.status.replaceAll("_", " ")}</AlertTitle>
              <AlertDescription>{match.message}</AlertDescription>
            </Alert>

            {match.providers.map((provider, index) => (
              <Card key={provider.id}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3 text-base">
                    <span>{index + 1}. {provider.business_name}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                      {provider.estimated_drive_minutes ? `${provider.estimated_drive_minutes} min` : "ETA n/a"}
                    </span>
                  </CardTitle>
                  <CardDescription>
                    {provider.city || "Unknown city"}, {provider.state || ""} · {provider.distance_miles.toFixed(1)} mi
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  {provider.phone && (
                    <p className="flex items-center gap-2 font-medium">
                      <Phone className="h-4 w-4" /> {provider.phone}
                    </p>
                  )}
                  <p className="text-muted-foreground">
                    Services: {provider.services.length ? provider.services.join(", ") : "Not specified"}
                  </p>
                  <p className="text-muted-foreground">
                    Rank score {provider.rank_score.toFixed(1)} · straight line {provider.straight_line_distance.toFixed(1)} mi
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
