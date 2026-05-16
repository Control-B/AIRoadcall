"use client";

import { useEffect, useMemo, useState } from "react";

export function isConfiguredMapboxToken(value?: string): value is string {
  const token = (value || "").trim();
  const normalized = token.toLowerCase();
  return (
    token.startsWith("pk.") &&
    normalized !== "pk.xxx" &&
    !normalized.includes("placeholder") &&
    !normalized.includes("replace_with")
  );
}

type MapboxTokenState = {
  token: string;
  configured: boolean;
  loading: boolean;
};

async function fetchRuntimeMapboxToken(): Promise<string> {
  for (const path of ["/mapbox-token", "/api/mapbox-token"]) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) continue;
      const body = await response.json();
      const runtimeToken = typeof body?.token === "string" ? body.token : "";
      if (isConfiguredMapboxToken(runtimeToken)) return runtimeToken.trim();
    } catch {
      // Try the next token endpoint.
    }
  }

  return "";
}

export function useMapboxToken(buildTimeToken?: string): MapboxTokenState {
  const initialToken = useMemo(() => {
    return isConfiguredMapboxToken(buildTimeToken) ? buildTimeToken.trim() : "";
  }, [buildTimeToken]);

  const [token, setToken] = useState(initialToken);
  const [loading, setLoading] = useState(!initialToken);

  useEffect(() => {
    if (initialToken) {
      setToken(initialToken);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    fetchRuntimeMapboxToken()
      .then((runtimeToken) => {
        if (cancelled) return;
        setToken(runtimeToken);
      })
      .catch(() => {
        if (!cancelled) setToken("");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [initialToken]);

  return { token, configured: Boolean(token), loading };
}