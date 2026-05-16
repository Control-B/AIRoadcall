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

    fetch("/api/mapbox-token", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (cancelled) return;
        const runtimeToken = typeof body?.token === "string" ? body.token : "";
        setToken(isConfiguredMapboxToken(runtimeToken) ? runtimeToken.trim() : "");
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