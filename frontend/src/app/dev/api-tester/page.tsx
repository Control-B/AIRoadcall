"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

// ─── Types ──────────────────────────────────────────────

interface ApiResponse {
  status: number;
  statusText: string;
  data: unknown;
  duration: number;
  timestamp: string;
}

interface HistoryEntry {
  id: string;
  method: string;
  path: string;
  status: number;
  duration: number;
  timestamp: string;
  request?: unknown;
  response: unknown;
}

// ─── Constants ──────────────────────────────────────────

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const ISSUE_TYPES = [
  "flat_tire",
  "dead_battery",
  "lockout",
  "fuel_delivery",
  "tow_needed",
  "engine_trouble",
  "overheating",
  "accident",
  "stuck_off_road",
  "other",
];

const MECHANIC_RESPONSES = [
  "accepted",
  "declined",
  "unavailable",
  "no_answer",
  "timed_out",
];

const TABS = [
  { id: "jobs", label: "🚗 Jobs", color: "bg-blue-500" },
  { id: "payments", label: "💳 Payments", color: "bg-green-500" },
  { id: "dispatch", label: "📡 Dispatch", color: "bg-purple-500" },
  { id: "tracking", label: "📍 Tracking", color: "bg-roadcall-orange" },
  { id: "mechanics", label: "🔧 Mechanics", color: "bg-red-500" },
  { id: "livekit", label: "📞 LiveKit", color: "bg-indigo-500" },
  { id: "pipeline", label: "🔄 Pipeline", color: "bg-cyan-500" },
  { id: "health", label: "❤️ Health", color: "bg-emerald-500" },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ─── Helpers ────────────────────────────────────────────

async function apiCall(
  method: string,
  path: string,
  body?: unknown
): Promise<ApiResponse> {
  const start = performance.now();
  const url = `${API_BASE}${path}`;

  try {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await res.json().catch(() => null);
    const duration = Math.round(performance.now() - start);

    return {
      status: res.status,
      statusText: res.statusText,
      data,
      duration,
      timestamp: new Date().toISOString(),
    };
  } catch (err: unknown) {
    const duration = Math.round(performance.now() - start);
    return {
      status: 0,
      statusText: "Network Error",
      data: {
        error: err instanceof Error ? err.message : "Failed to connect",
        hint: "Is the FastAPI backend running on localhost:8000?",
      },
      duration,
      timestamp: new Date().toISOString(),
    };
  }
}

function getStatusColor(status: number): string {
  if (status === 0) return "text-gray-500";
  if (status < 300) return "text-emerald-600";
  if (status < 400) return "text-yellow-600";
  if (status < 500) return "text-roadcall-orange";
  return "text-red-600";
}

function getMethodColor(method: string): string {
  switch (method) {
    case "GET":
      return "bg-blue-100 text-blue-800";
    case "POST":
      return "bg-green-100 text-green-800";
    case "PUT":
      return "bg-amber-100 text-amber-800";
    case "PATCH":
      return "bg-roadcall-orange/10 text-roadcall-orange";
    case "DELETE":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

// ─── Response Viewer ────────────────────────────────────

function ResponseViewer({ response }: { response: ApiResponse | null }) {
  if (!response) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center">
        <p className="text-sm text-muted-foreground">
          Send a request to see the response here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Status bar */}
      <div className="flex items-center gap-3 rounded-lg bg-slate-50 p-3">
        <span
          className={`text-lg font-bold ${getStatusColor(response.status)}`}
        >
          {response.status || "ERR"}
        </span>
        <span className="text-sm text-muted-foreground">
          {response.statusText}
        </span>
        <span className="ml-auto text-xs text-muted-foreground">
          ⏱ {response.duration}ms
        </span>
      </div>

      {/* JSON body */}
      <div className="relative">
        <pre className="max-h-96 overflow-auto rounded-lg bg-roadcall-ink p-4 text-xs text-slate-100">
          {JSON.stringify(response.data, null, 2)}
        </pre>
        <button
          className="absolute right-2 top-2 rounded bg-slate-700 px-2 py-1 text-xs text-roadcall-silver/85 hover:bg-slate-600"
          onClick={() =>
            navigator.clipboard.writeText(
              JSON.stringify(response.data, null, 2)
            )
          }
        >
          Copy
        </button>
      </div>
    </div>
  );
}

// ─── Field Component ────────────────────────────────────

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-slate-700">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

// ─── Endpoint Card ──────────────────────────────────────

function EndpointCard({
  method,
  path,
  description,
  children,
  onSubmit,
  loading,
}: {
  method: string;
  path: string;
  description: string;
  children: React.ReactNode;
  onSubmit: () => void;
  loading: boolean;
}) {
  return (
    <Card className="border-l-4 border-l-blue-400">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Badge className={getMethodColor(method)}>{method}</Badge>
          <code className="text-sm font-mono text-slate-700">{path}</code>
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {children}
        <Button
          onClick={onSubmit}
          disabled={loading}
          size="sm"
          className="w-full"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Sending...
            </span>
          ) : (
            `Send ${method} Request`
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Tab Panels ─────────────────────────────────────────

function JobsPanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);

  // Create job state
  const [driverName, setDriverName] = useState("Jane Smith");
  const [driverPhone, setDriverPhone] = useState("+15551234567");
  const [vehicleType, setVehicleType] = useState("2022 Honda Civic");
  const [issueType, setIssueType] = useState("flat_tire");
  const [issueSummary, setIssueSummary] = useState(
    "Front left tire is completely flat"
  );
  const [holdAmount, setHoldAmount] = useState("150.00");

  // Token state (for get/location endpoints)
  const [token, setToken] = useState("");
  const [lat, setLat] = useState("34.0522");
  const [lng, setLng] = useState("-118.2437");

  const fire = async (
    id: string,
    method: string,
    path: string,
    body?: unknown
  ) => {
    setLoading(id);
    const res = await apiCall(method, path, body);
    onResponse(res);
    addHistory({
      id: Date.now().toString(),
      method,
      path,
      status: res.status,
      duration: res.duration,
      timestamp: res.timestamp,
      request: body,
      response: res.data,
    });

    // Auto-capture token from create response
    if (id === "create" && res.status === 201) {
      const data = res.data as Record<string, unknown>;
      if (data?.magic_link_token) {
        setToken(data.magic_link_token as string);
      }
    }

    setLoading(null);
  };

  return (
    <div className="space-y-6">
      {/* CREATE JOB */}
      <EndpointCard
        method="POST"
        path="/jobs"
        description="Create a new roadside job (simulates post-call intake). Returns a magic link token you can use below."
        onSubmit={() =>
          fire("create", "POST", "/jobs", {
            driver_name: driverName,
            driver_phone: driverPhone,
            vehicle_type: vehicleType || null,
            issue_type: issueType,
            issue_summary: issueSummary || null,
            payment_hold_amount: holdAmount ? parseFloat(holdAmount) : null,
          })
        }
        loading={loading === "create"}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Driver Name">
            <Input
              value={driverName}
              onChange={(e) => setDriverName(e.target.value)}
            />
          </Field>
          <Field label="Driver Phone">
            <Input
              value={driverPhone}
              onChange={(e) => setDriverPhone(e.target.value)}
            />
          </Field>
          <Field label="Vehicle Type">
            <Input
              value={vehicleType}
              onChange={(e) => setVehicleType(e.target.value)}
            />
          </Field>
          <Field label="Issue Type">
            <Select
              value={issueType}
              onChange={(e) => setIssueType(e.target.value)}
            >
              {ISSUE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Issue Summary" hint="Optional details">
            <Input
              value={issueSummary}
              onChange={(e) => setIssueSummary(e.target.value)}
            />
          </Field>
          <Field label="Hold Amount ($)" hint="Authorization hold">
            <Input
              type="number"
              value={holdAmount}
              onChange={(e) => setHoldAmount(e.target.value)}
            />
          </Field>
        </div>
      </EndpointCard>

      {/* Divider with auto-captured token */}
      <div className="rounded-lg bg-blue-50 p-3">
        <Field
          label="🔑 Magic Link Token"
          hint="Paste from the Create Job response, or it auto-fills after creating a job"
        >
          <Input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste magic_link_token here..."
            className="font-mono text-xs"
          />
        </Field>
      </div>

      {/* GET JOB BY TOKEN */}
      <EndpointCard
        method="GET"
        path="/jobs/{token}"
        description="Retrieve driver-facing job data by magic link token"
        onSubmit={() => fire("get", "GET", `/jobs/${token}`)}
        loading={loading === "get"}
      >
        <p className="text-xs text-muted-foreground">
          Uses the token above: <code className="text-blue-600">{token || "(empty)"}</code>
        </p>
      </EndpointCard>

      {/* UPDATE LOCATION */}
      <EndpointCard
        method="POST"
        path="/jobs/{token}/location"
        description="Save driver GPS coordinates from browser geolocation"
        onSubmit={() =>
          fire("location", "POST", `/jobs/${token}/location`, {
            lat: parseFloat(lat),
            lng: parseFloat(lng),
          })
        }
        loading={loading === "location"}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Latitude">
            <Input
              type="number"
              step="any"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
            />
          </Field>
          <Field label="Longitude">
            <Input
              type="number"
              step="any"
              value={lng}
              onChange={(e) => setLng(e.target.value)}
            />
          </Field>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            if (navigator.geolocation) {
              navigator.geolocation.getCurrentPosition((pos) => {
                setLat(pos.coords.latitude.toString());
                setLng(pos.coords.longitude.toString());
              });
            }
          }}
        >
          📍 Use My Location
        </Button>
      </EndpointCard>

      {/* GET STATUS */}
      <EndpointCard
        method="GET"
        path="/jobs/{token}/status"
        description="Poll current job status (used by frontend for live updates)"
        onSubmit={() => fire("status", "GET", `/jobs/${token}/status`)}
        loading={loading === "status"}
      >
        <p className="text-xs text-muted-foreground">
          Uses the token above: <code className="text-blue-600">{token || "(empty)"}</code>
        </p>
      </EndpointCard>
    </div>
  );
}

function PaymentsPanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [amount, setAmount] = useState("");
  const [paymentIntentId, setPaymentIntentId] = useState("");

  const fire = async (
    id: string,
    method: string,
    path: string,
    body?: unknown
  ) => {
    setLoading(id);
    const res = await apiCall(method, path, body);
    onResponse(res);
    addHistory({
      id: Date.now().toString(),
      method,
      path,
      status: res.status,
      duration: res.duration,
      timestamp: res.timestamp,
      request: body,
      response: res.data,
    });

    // Auto-capture payment intent ID
    if (id === "create-pi" && res.status === 200) {
      const data = res.data as Record<string, unknown>;
      if (data?.payment_intent_id) {
        setPaymentIntentId(data.payment_intent_id as string);
      }
    }

    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-green-50 p-3">
        <Field
          label="🔑 Magic Link Token"
          hint="Use the token from Job creation"
        >
          <Input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste magic_link_token here..."
            className="font-mono text-xs"
          />
        </Field>
      </div>

      {/* CREATE PAYMENT INTENT */}
      <EndpointCard
        method="POST"
        path="/jobs/{token}/payment-intent"
        description="Create a Stripe PaymentIntent with manual capture (authorization hold). Requires Stripe keys configured."
        onSubmit={() =>
          fire("create-pi", "POST", `/jobs/${token}/payment-intent`, {
            amount: amount ? parseFloat(amount) : null,
          })
        }
        loading={loading === "create-pi"}
      >
        <Field
          label="Override Amount ($)"
          hint="Leave empty to use the job's hold amount"
        >
          <Input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="e.g., 150.00"
          />
        </Field>
      </EndpointCard>

      {/* CONFIRM PAYMENT */}
      <EndpointCard
        method="POST"
        path="/jobs/{token}/payment-confirm"
        description="Confirm that the frontend completed payment authorization"
        onSubmit={() =>
          fire("confirm", "POST", `/jobs/${token}/payment-confirm`, {
            payment_intent_id: paymentIntentId,
          })
        }
        loading={loading === "confirm"}
      >
        <Field
          label="Payment Intent ID"
          hint="Auto-filled from Create PaymentIntent response"
        >
          <Input
            value={paymentIntentId}
            onChange={(e) => setPaymentIntentId(e.target.value)}
            placeholder="pi_..."
            className="font-mono text-xs"
          />
        </Field>
      </EndpointCard>
    </div>
  );
}

function DispatchPanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);
  const [jobId, setJobId] = useState("");
  const [dispatchAttemptId, setDispatchAttemptId] = useState("");
  const [mechResponse, setMechResponse] = useState("accepted");
  const [etaMinutes, setEtaMinutes] = useState("25");
  const [notes, setNotes] = useState("");

  const fire = async (
    id: string,
    method: string,
    path: string,
    body?: unknown
  ) => {
    setLoading(id);
    const res = await apiCall(method, path, body);
    onResponse(res);
    addHistory({
      id: Date.now().toString(),
      method,
      path,
      status: res.status,
      duration: res.duration,
      timestamp: res.timestamp,
      request: body,
      response: res.data,
    });

    // Auto-capture dispatch attempt ID
    if (id === "next" && res.status === 200) {
      const data = res.data as Record<string, unknown>;
      if (data?.dispatch_attempt_id) {
        setDispatchAttemptId(data.dispatch_attempt_id as string);
      }
    }

    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-purple-50 p-3">
        <Field
          label="🆔 Job ID (UUID)"
          hint="Internal job UUID — you can find this in the database or audit logs. Not the public_job_id."
        >
          <Input
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
            placeholder="e.g., 550e8400-e29b-41d4-a716-446655440000"
            className="font-mono text-xs"
          />
        </Field>
      </div>

      {/* START DISPATCH */}
      <EndpointCard
        method="POST"
        path="/dispatch/{job_id}/start"
        description="Begin mechanic matching. Job must have payment authorized."
        onSubmit={() => fire("start", "POST", `/dispatch/${jobId}/start`)}
        loading={loading === "start"}
      >
        <p className="text-xs text-muted-foreground">
          This transitions the job to <code>matching_mechanics</code> status.
        </p>
      </EndpointCard>

      {/* DISPATCH NEXT */}
      <EndpointCard
        method="POST"
        path="/dispatch/{job_id}/next"
        description="Select and queue the next best-ranked mechanic"
        onSubmit={() => fire("next", "POST", `/dispatch/${jobId}/next`)}
        loading={loading === "next"}
      >
        <p className="text-xs text-muted-foreground">
          Returns the mechanic details and dispatch attempt ID.
        </p>
      </EndpointCard>

      {/* MECHANIC RESPONSE */}
      <EndpointCard
        method="POST"
        path="/dispatch/{job_id}/mechanic-response"
        description="Record a mechanic's response to the dispatch attempt"
        onSubmit={() =>
          fire("response", "POST", `/dispatch/${jobId}/mechanic-response`, {
            dispatch_attempt_id: dispatchAttemptId,
            response: mechResponse,
            eta_minutes: etaMinutes ? parseInt(etaMinutes) : null,
            notes: notes || null,
          })
        }
        loading={loading === "response"}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Dispatch Attempt ID" hint="Auto-fills from /next">
            <Input
              value={dispatchAttemptId}
              onChange={(e) => setDispatchAttemptId(e.target.value)}
              className="font-mono text-xs"
            />
          </Field>
          <Field label="Mechanic Response">
            <Select
              value={mechResponse}
              onChange={(e) => setMechResponse(e.target.value)}
            >
              {MECHANIC_RESPONSES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="ETA (minutes)">
            <Input
              type="number"
              value={etaMinutes}
              onChange={(e) => setEtaMinutes(e.target.value)}
            />
          </Field>
          <Field label="Notes">
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional..."
            />
          </Field>
        </div>
      </EndpointCard>
    </div>
  );
}

function TrackingPanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState("");
  const [polling, setPolling] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fire = async () => {
    setLoading(true);
    const res = await apiCall("GET", `/jobs/${token}/tracking`);
    onResponse(res);
    addHistory({
      id: Date.now().toString(),
      method: "GET",
      path: `/jobs/${token}/tracking`,
      status: res.status,
      duration: res.duration,
      timestamp: res.timestamp,
      response: res.data,
    });
    setLoading(false);
  };

  const togglePolling = () => {
    if (polling) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setPolling(false);
    } else {
      fire();
      intervalRef.current = setInterval(fire, 5000);
      setPolling(true);
    }
  };

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-roadcall-panel/40 p-3">
        <Field label="🔑 Magic Link Token" hint="Use the token from Job creation">
          <Input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste magic_link_token here..."
            className="font-mono text-xs"
          />
        </Field>
      </div>

      <EndpointCard
        method="GET"
        path="/jobs/{token}/tracking"
        description="Return tracking payload with driver/mechanic GPS, ETA, and status"
        onSubmit={fire}
        loading={loading}
      >
        <div className="flex items-center gap-3">
          <Button
            variant={polling ? "destructive" : "outline"}
            size="sm"
            onClick={togglePolling}
          >
            {polling ? "⏹ Stop Polling" : "▶ Poll every 5s"}
          </Button>
          {polling && (
            <Badge variant="warning">
              <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-amber-500" />
              Polling active
            </Badge>
          )}
        </div>
      </EndpointCard>
    </div>
  );
}

function MechanicsPanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);

  // Create mechanic
  const [companyName, setCompanyName] = useState("QuickFix Auto");
  const [contactName, setContactName] = useState("Mike Johnson");
  const [phone, setPhone] = useState("+15559876543");
  const [serviceTypes, setServiceTypes] = useState(
    "flat_tire,dead_battery,lockout"
  );
  const [vehicleTypes, setVehicleTypes] = useState("sedan,suv,truck");
  const [baseLat, setBaseLat] = useState("34.0522");
  const [baseLng, setBaseLng] = useState("-118.2437");
  const [rating, setRating] = useState("4.5");

  // Update location
  const [mechId, setMechId] = useState("");
  const [mechLat, setMechLat] = useState("34.0530");
  const [mechLng, setMechLng] = useState("-118.2400");

  const fire = async (
    id: string,
    method: string,
    path: string,
    body?: unknown
  ) => {
    setLoading(id);
    const res = await apiCall(method, path, body);
    onResponse(res);
    addHistory({
      id: Date.now().toString(),
      method,
      path,
      status: res.status,
      duration: res.duration,
      timestamp: res.timestamp,
      request: body,
      response: res.data,
    });

    // Auto-capture mechanic ID
    if (id === "create" && res.status === 201) {
      const data = res.data as Record<string, unknown>;
      if (data?.id) {
        setMechId(data.id as string);
      }
    }

    setLoading(null);
  };

  return (
    <div className="space-y-6">
      {/* CREATE MECHANIC */}
      <EndpointCard
        method="POST"
        path="/mechanics"
        description="Create or upsert a mechanic record (by phone number)"
        onSubmit={() =>
          fire("create", "POST", "/mechanics", {
            company_name: companyName,
            contact_name: contactName,
            phone: phone,
            service_types: serviceTypes
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            vehicle_types_supported: vehicleTypes
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            base_lat: parseFloat(baseLat),
            base_lng: parseFloat(baseLng),
            active: true,
            accepts_mobile_roadside: true,
            rating: rating ? parseFloat(rating) : null,
          })
        }
        loading={loading === "create"}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Company Name">
            <Input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
            />
          </Field>
          <Field label="Contact Name">
            <Input
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
            />
          </Field>
          <Field label="Phone">
            <Input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </Field>
          <Field label="Rating">
            <Input
              type="number"
              step="0.1"
              value={rating}
              onChange={(e) => setRating(e.target.value)}
            />
          </Field>
          <Field label="Service Types" hint="Comma separated">
            <Input
              value={serviceTypes}
              onChange={(e) => setServiceTypes(e.target.value)}
            />
          </Field>
          <Field label="Vehicle Types" hint="Comma separated">
            <Input
              value={vehicleTypes}
              onChange={(e) => setVehicleTypes(e.target.value)}
            />
          </Field>
          <Field label="Base Latitude">
            <Input
              type="number"
              step="any"
              value={baseLat}
              onChange={(e) => setBaseLat(e.target.value)}
            />
          </Field>
          <Field label="Base Longitude">
            <Input
              type="number"
              step="any"
              value={baseLng}
              onChange={(e) => setBaseLng(e.target.value)}
            />
          </Field>
        </div>
      </EndpointCard>

      {/* UPDATE MECHANIC LOCATION */}
      <div className="rounded-lg bg-red-50 p-3">
        <Field
          label="🆔 Mechanic ID (UUID)"
          hint="Auto-fills after creating a mechanic"
        >
          <Input
            value={mechId}
            onChange={(e) => setMechId(e.target.value)}
            placeholder="Mechanic UUID..."
            className="font-mono text-xs"
          />
        </Field>
      </div>

      <EndpointCard
        method="POST"
        path="/mechanics/{id}/location"
        description="Update mechanic live GPS location for tracking"
        onSubmit={() =>
          fire("location", "POST", `/mechanics/${mechId}/location`, {
            lat: parseFloat(mechLat),
            lng: parseFloat(mechLng),
          })
        }
        loading={loading === "location"}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Latitude">
            <Input
              type="number"
              step="any"
              value={mechLat}
              onChange={(e) => setMechLat(e.target.value)}
            />
          </Field>
          <Field label="Longitude">
            <Input
              type="number"
              step="any"
              value={mechLng}
              onChange={(e) => setMechLng(e.target.value)}
            />
          </Field>
        </div>
      </EndpointCard>
    </div>
  );
}

function LiveKitPanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);

  // Simulate driver intake completed
  const [driverName, setDriverName] = useState("Jane Smith");
  const [driverPhone, setDriverPhone] = useState("+15551234567");
  const [vehicleType, setVehicleType] = useState("2022 Honda Civic");
  const [issueType, setIssueType] = useState("flat_tire");
  const [issueSummary, setIssueSummary] = useState(
    "Front left tire is flat, pulled over on highway shoulder"
  );

  // Simulate mechanic dispatch result
  const [dispatchJobId, setDispatchJobId] = useState("");
  const [dispatchAttemptId, setDispatchAttemptId] = useState("");
  const [mechName, setMechName] = useState("QuickFix Auto");
  const [mechPhone, setMechPhone] = useState("+15559876543");
  const [mechResponse, setMechResponse] = useState("accepted");
  const [mechEta, setMechEta] = useState("20");

  const fire = async (
    id: string,
    method: string,
    path: string,
    body?: unknown
  ) => {
    setLoading(id);
    const res = await apiCall(method, path, body);
    onResponse(res);
    addHistory({
      id: Date.now().toString(),
      method,
      path,
      status: res.status,
      duration: res.duration,
      timestamp: res.timestamp,
      request: body,
      response: res.data,
    });
    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-indigo-50 p-3 text-sm text-indigo-700">
        💡 <strong>LiveKit Cloud</strong> handles AI telephony for this system.
        These simulate webhook payloads that LiveKit would send to{" "}
        <code className="rounded bg-indigo-100 px-1">/webhooks/livekit</code>
        {" "}after call events.
      </div>

      {/* SIMULATE DRIVER INTAKE COMPLETED */}
      <EndpointCard
        method="POST"
        path="/webhooks/livekit"
        description="Simulate: Driver intake call completed (room_finished with driver_intake type). Creates a job + sends magic link."
        onSubmit={() =>
          fire("intake", "POST", "/webhooks/livekit", {
            event: "room_finished",
            room: {
              name: `intake-${Date.now()}`,
              metadata: JSON.stringify({
                type: "driver_intake",
                agent_collected_data: {
                  driver_name: driverName,
                  driver_phone: driverPhone,
                  vehicle_type: vehicleType,
                  issue_type: issueType,
                  issue_summary: issueSummary,
                },
              }),
              num_participants: 2,
            },
            participants: [],
          })
        }
        loading={loading === "intake"}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Driver Name">
            <Input
              value={driverName}
              onChange={(e) => setDriverName(e.target.value)}
            />
          </Field>
          <Field label="Driver Phone">
            <Input
              value={driverPhone}
              onChange={(e) => setDriverPhone(e.target.value)}
            />
          </Field>
          <Field label="Vehicle Type">
            <Input
              value={vehicleType}
              onChange={(e) => setVehicleType(e.target.value)}
            />
          </Field>
          <Field label="Issue Type">
            <Select
              value={issueType}
              onChange={(e) => setIssueType(e.target.value)}
            >
              {ISSUE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </Field>
          <div className="col-span-2">
            <Field label="Issue Summary">
              <Input
                value={issueSummary}
                onChange={(e) => setIssueSummary(e.target.value)}
              />
            </Field>
          </div>
        </div>
      </EndpointCard>

      {/* SIMULATE MECHANIC DISPATCH CALL ENDED */}
      <div className="rounded-lg bg-indigo-50 p-3 space-y-3">
        <Field
          label="🆔 Job ID (UUID)"
          hint="Internal job UUID for the dispatch simulation"
        >
          <Input
            value={dispatchJobId}
            onChange={(e) => setDispatchJobId(e.target.value)}
            placeholder="Job UUID..."
            className="font-mono text-xs"
          />
        </Field>
        <Field
          label="🆔 Dispatch Attempt ID"
          hint="Dispatch attempt UUID"
        >
          <Input
            value={dispatchAttemptId}
            onChange={(e) => setDispatchAttemptId(e.target.value)}
            placeholder="Dispatch attempt UUID..."
            className="font-mono text-xs"
          />
        </Field>
      </div>

      <EndpointCard
        method="POST"
        path="/webhooks/livekit"
        description="Simulate: Mechanic dispatch call ended (room_finished with mechanic_dispatch type). Records the mechanic's response."
        onSubmit={() =>
          fire("dispatch-result", "POST", "/webhooks/livekit", {
            event: "room_finished",
            room: {
              name: `dispatch-${dispatchAttemptId || "test"}`,
              metadata: JSON.stringify({
                type: "mechanic_dispatch",
                job_id: dispatchJobId,
                dispatch_attempt_id: dispatchAttemptId,
                mechanic_name: mechName,
                mechanic_phone: mechPhone,
                agent_result: {
                  response: mechResponse,
                  eta_minutes: mechEta ? parseInt(mechEta) : null,
                  notes: "Simulated via API tester",
                },
              }),
              num_participants: 2,
            },
            participants: [],
          })
        }
        loading={loading === "dispatch-result"}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Mechanic Name">
            <Input
              value={mechName}
              onChange={(e) => setMechName(e.target.value)}
            />
          </Field>
          <Field label="Mechanic Phone">
            <Input
              value={mechPhone}
              onChange={(e) => setMechPhone(e.target.value)}
            />
          </Field>
          <Field label="Response">
            <Select
              value={mechResponse}
              onChange={(e) => setMechResponse(e.target.value)}
            >
              {MECHANIC_RESPONSES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="ETA (minutes)">
            <Input
              type="number"
              value={mechEta}
              onChange={(e) => setMechEta(e.target.value)}
            />
          </Field>
        </div>
      </EndpointCard>

      {/* SIMULATE SIP NO-ANSWER */}
      <EndpointCard
        method="POST"
        path="/webhooks/livekit"
        description="Simulate: SIP call failed (mechanic didn't pick up, busy signal, etc.)"
        onSubmit={() =>
          fire("sip-fail", "POST", "/webhooks/livekit", {
            event: "room_finished",
            room: {
              name: `dispatch-${dispatchAttemptId || "test"}`,
              metadata: JSON.stringify({
                type: "mechanic_dispatch",
                job_id: dispatchJobId,
                dispatch_attempt_id: dispatchAttemptId,
                mechanic_name: mechName,
                mechanic_phone: mechPhone,
              }),
              num_participants: 1, // Only agent — mechanic never joined
            },
            participants: [],
          })
        }
        loading={loading === "sip-fail"}
      >
        <p className="text-xs text-muted-foreground">
          Simulates a call where only the AI agent was in the room (mechanic
          never picked up). Will auto-mark as <code>no_answer</code> and
          trigger next dispatch.
        </p>
      </EndpointCard>
    </div>
  );
}

function PipelinePanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);

  const fire = async (
    id: string,
    method: string,
    path: string,
    body?: unknown
  ) => {
    setLoading(id);
    const res = await apiCall(method, path, body);
    onResponse(res);
    addHistory({
      id: Date.now().toString(),
      method,
      path,
      status: res.status,
      duration: res.duration,
      timestamp: res.timestamp,
      request: body,
      response: res.data,
    });

    // Auto-capture run_id from scrape response
    if (id === "scrape" && res.status < 300) {
      const data = res.data as Record<string, unknown>;
      if (data?.run_id) {
        setRunId(data.run_id as string);
      }
    }

    setLoading(null);
  };

  const [scrapeLocation, setScrapeLocation] = useState("Austin, TX");
  const [scrapeRadius, setScrapeRadius] = useState("25");
  const [scrapeMaxResults, setScrapeMaxResults] = useState("50");
  const [runId, setRunId] = useState("");
  const [enrichIds, setEnrichIds] = useState("");
  const [enrichMaxAge, setEnrichMaxAge] = useState("168");
  const [enrichLimit, setEnrichLimit] = useState("20");

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-cyan-50 p-3 text-sm text-cyan-800">
        💡 <strong>Mechanic Data Pipeline</strong> — Seed your database with
        Apify (Google Maps scraping), then enrich with Tavily (real-time
        verification). View stats to monitor data quality.
      </div>

      {/* Scrape */}
      <EndpointCard
        method="POST"
        path="/pipeline/scrape"
        description="Start Apify scrape — trigger a Google Maps search for mechanics in an area"
        onSubmit={() =>
          fire("scrape", "POST", "/pipeline/scrape", {
            location: scrapeLocation,
            radius_miles: parseInt(scrapeRadius),
            max_results: parseInt(scrapeMaxResults),
          })
        }
        loading={loading === "scrape"}
      >
        <Input
          placeholder="Location (e.g. Austin, TX)"
          value={scrapeLocation}
          onChange={(e) => setScrapeLocation(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <Input
            placeholder="Radius (miles)"
            value={scrapeRadius}
            onChange={(e) => setScrapeRadius(e.target.value)}
          />
          <Input
            placeholder="Max results"
            value={scrapeMaxResults}
            onChange={(e) => setScrapeMaxResults(e.target.value)}
          />
        </div>
      </EndpointCard>

      {/* Check Status */}
      <EndpointCard
        method="GET"
        path="/pipeline/scrape/{run_id}"
        description="Check scrape status — poll an Apify run for completion"
        onSubmit={() => fire("scrape-status", "GET", `/pipeline/scrape/${runId}`)}
        loading={loading === "scrape-status"}
      >
        <Input
          placeholder="Run ID from start scrape response"
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
        />
      </EndpointCard>

      {/* Import Results */}
      <EndpointCard
        method="POST"
        path="/pipeline/scrape/{run_id}/import"
        description="Import results — fetch completed scrape data and upsert into mechanic DB"
        onSubmit={() =>
          fire("import", "POST", `/pipeline/scrape/${runId}/import`)
        }
        loading={loading === "import"}
      >
        <Input
          placeholder="Run ID (same as above)"
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
        />
        <p className="text-xs text-gray-500">
          Run must be SUCCEEDED before importing.
        </p>
      </EndpointCard>

      {/* Enrich */}
      <EndpointCard
        method="POST"
        path="/pipeline/enrich"
        description="Enrich mechanics (Tavily) — verify & enrich with real-time web search"
        onSubmit={() =>
          fire("enrich", "POST", "/pipeline/enrich", {
            mechanic_ids: enrichIds
              ? enrichIds.split(",").map((s) => s.trim())
              : null,
            max_age_hours: parseInt(enrichMaxAge),
            limit: parseInt(enrichLimit),
          })
        }
        loading={loading === "enrich"}
      >
        <Input
          placeholder="Mechanic IDs (comma-separated, or empty for stale)"
          value={enrichIds}
          onChange={(e) => setEnrichIds(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <Input
            placeholder="Max age (hours)"
            value={enrichMaxAge}
            onChange={(e) => setEnrichMaxAge(e.target.value)}
          />
          <Input
            placeholder="Limit"
            value={enrichLimit}
            onChange={(e) => setEnrichLimit(e.target.value)}
          />
        </div>
      </EndpointCard>

      {/* Stats */}
      <EndpointCard
        method="GET"
        path="/pipeline/stats"
        description="Pipeline stats — mechanic count, sources, enrichment freshness, dispatch metrics"
        onSubmit={() => fire("stats", "GET", "/pipeline/stats")}
        loading={loading === "stats"}
      >
        <p className="text-xs text-gray-500">
          No parameters needed. Shows total mechanics, sources, stale count,
          and dispatch performance.
        </p>
      </EndpointCard>
    </div>
  );
}

function HealthPanel({
  onResponse,
  addHistory,
}: {
  onResponse: (r: ApiResponse) => void;
  addHistory: (h: HistoryEntry) => void;
}) {
  const [loading, setLoading] = useState(false);

  const fire = async () => {
    setLoading(true);
    // Health check is at root, not under /api
    const base = API_BASE.replace(/\/api$/, "");
    const start = performance.now();
    try {
      const res = await fetch(`${base}/health`);
      const data = await res.json();
      const duration = Math.round(performance.now() - start);
      const apiRes: ApiResponse = {
        status: res.status,
        statusText: res.statusText,
        data,
        duration,
        timestamp: new Date().toISOString(),
      };
      onResponse(apiRes);
      addHistory({
        id: Date.now().toString(),
        method: "GET",
        path: "/health",
        status: apiRes.status,
        duration: apiRes.duration,
        timestamp: apiRes.timestamp,
        response: apiRes.data,
      });
    } catch (err: unknown) {
      const duration = Math.round(performance.now() - start);
      const apiRes: ApiResponse = {
        status: 0,
        statusText: "Network Error",
        data: {
          error: err instanceof Error ? err.message : "Failed to connect",
          hint: "Is the FastAPI backend running? Try: uvicorn app.main:app --reload",
        },
        duration,
        timestamp: new Date().toISOString(),
      };
      onResponse(apiRes);
      addHistory({
        id: Date.now().toString(),
        method: "GET",
        path: "/health",
        status: 0,
        duration,
        timestamp: apiRes.timestamp,
        response: apiRes.data,
      });
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <EndpointCard
        method="GET"
        path="/health"
        description='Quick health check — should return {"status": "healthy"}'
        onSubmit={fire}
        loading={loading}
      >
        <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
          💡 <strong>Tip:</strong> Start the backend with:{" "}
          <code className="rounded bg-emerald-100 px-1">
            cd backend && uvicorn app.main:app --reload
          </code>
        </div>
      </EndpointCard>
    </div>
  );
}

// ─── Main Page ──────────────────────────────────────────

export default function ApiTesterPage() {
  const [activeTab, setActiveTab] = useState<TabId>("health");
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const addHistory = useCallback((entry: HistoryEntry) => {
    setHistory((prev) => [entry, ...prev].slice(0, 50)); // Keep last 50
  }, []);

  const activeTabConfig = TABS.find((t) => t.id === activeTab)!;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="border-b bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                🛠️ API Testing Dashboard
              </h1>
              <p className="text-sm text-muted-foreground">
                AI Roadside Support — Interactive API Explorer
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="text-xs">
                {API_BASE}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
              >
                📋 History ({history.length})
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Left sidebar: Tabs */}
          <div className="col-span-12 lg:col-span-2">
            <nav className="flex flex-row gap-1 lg:flex-col lg:gap-2">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setResponse(null);
                  }}
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
                      : "text-roadcall-muted/55 hover:bg-roadcall-panel/450 hover:text-slate-900"
                  }`}
                >
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>

            {/* Quick info */}
            <div className="mt-6 hidden rounded-lg bg-white p-4 shadow-sm ring-1 ring-slate-200 lg:block">
              <h3 className="text-xs font-semibold uppercase text-roadcall-muted/70">
                Workflow
              </h3>
              <ol className="mt-2 space-y-1 text-xs text-roadcall-muted/55">
                <li>1. Check ❤️ Health</li>
                <li>2. Create 🔧 Mechanic</li>
                <li>3. Create 🚗 Job</li>
                <li>4. POST Location</li>
                <li>5. Create 💳 Payment</li>
                <li>6. Start 📡 Dispatch</li>
                <li>7. Sim 📞 LiveKit call</li>
                <li>8. 🔄 Seed DB via Pipeline</li>
                <li>8. Watch 📍 Tracking</li>
              </ol>
            </div>
          </div>

          {/* Center: Endpoint forms */}
          <div className="col-span-12 lg:col-span-5">
            <div className="mb-4 flex items-center gap-2">
              <div
                className={`h-3 w-3 rounded-full ${activeTabConfig.color}`}
              />
              <h2 className="text-lg font-semibold text-slate-900">
                {activeTabConfig.label}
              </h2>
            </div>

            {activeTab === "jobs" && (
              <JobsPanel onResponse={setResponse} addHistory={addHistory} />
            )}
            {activeTab === "payments" && (
              <PaymentsPanel onResponse={setResponse} addHistory={addHistory} />
            )}
            {activeTab === "dispatch" && (
              <DispatchPanel onResponse={setResponse} addHistory={addHistory} />
            )}
            {activeTab === "tracking" && (
              <TrackingPanel onResponse={setResponse} addHistory={addHistory} />
            )}
            {activeTab === "mechanics" && (
              <MechanicsPanel
                onResponse={setResponse}
                addHistory={addHistory}
              />
            )}
            {activeTab === "livekit" && (
              <LiveKitPanel
                onResponse={setResponse}
                addHistory={addHistory}
              />
            )}
            {activeTab === "pipeline" && (
              <PipelinePanel
                onResponse={setResponse}
                addHistory={addHistory}
              />
            )}
            {activeTab === "health" && (
              <HealthPanel onResponse={setResponse} addHistory={addHistory} />
            )}
          </div>

          {/* Right: Response + History */}
          <div className="col-span-12 lg:col-span-5">
            <div className="sticky top-6 space-y-6">
              {/* Response Viewer */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Response</CardTitle>
                  <CardDescription>
                    Latest API response from the backend
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponseViewer response={response} />
                </CardContent>
              </Card>

              {/* History */}
              {showHistory && (
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">
                        Request History
                      </CardTitle>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setHistory([])}
                      >
                        Clear
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-80 space-y-2 overflow-auto">
                      {history.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No requests yet
                        </p>
                      ) : (
                        history.map((entry) => (
                          <button
                            key={entry.id}
                            onClick={() =>
                              setResponse({
                                status: entry.status,
                                statusText: "",
                                data: entry.response,
                                duration: entry.duration,
                                timestamp: entry.timestamp,
                              })
                            }
                            className="flex w-full items-center gap-2 rounded-md p-2 text-left text-xs hover:bg-slate-50"
                          >
                            <Badge
                              className={`${getMethodColor(entry.method)} text-[10px]`}
                            >
                              {entry.method}
                            </Badge>
                            <span className="flex-1 truncate font-mono text-roadcall-muted/55">
                              {entry.path}
                            </span>
                            <span
                              className={`font-bold ${getStatusColor(entry.status)}`}
                            >
                              {entry.status || "ERR"}
                            </span>
                            <span className="text-roadcall-muted">
                              {entry.duration}ms
                            </span>
                          </button>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
