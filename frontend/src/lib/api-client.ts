function getApiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      return "/api";
    }
  }

  return (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/$/, "");
}

interface ApiErrorBody {
  detail?: string | { message?: string } | Array<{ msg?: string }>;
  message?: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let errorMessage = "Request failed";
    try {
      const body = (await res.json()) as ApiErrorBody;
      if (typeof body.detail === "string") {
        errorMessage = body.detail;
      } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        errorMessage = body.detail[0].msg as string;
      } else if (
        body.detail &&
        typeof body.detail === "object" &&
        "message" in body.detail
      ) {
        errorMessage = (body.detail.message as string) || errorMessage;
      } else if (body.message) {
        errorMessage = body.message;
      }
    } catch {
      // Keep default message when response body is not JSON.
    }
    throw new Error(errorMessage);
  }

  return (await res.json()) as T;
}

export interface AssignedMechanic {
  id?: string;
  company_name?: string;
  contact_name?: string;
  eta_minutes?: number | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  lat?: number | null;
  lng?: number | null;
}

export interface JobDriverView {
  public_job_id: string;
  status: string;
  payment_status?: string | null;
  driver_name: string;
  issue_type: string;
  issue_summary?: string | null;
  vehicle_type?: string | null;
  driver_city?: string | null;
  driver_state?: string | null;
  driver_lat?: number | null;
  driver_lng?: number | null;
  payment_hold_amount: number | null;
  assigned_mechanic?: AssignedMechanic | null;
  driver_eta_decision?: string | null;
}

export interface LocationUpdateResponse {
  success: boolean;
  status: string;
  driver_lat: number;
  driver_lng: number;
}

export interface JobCodeLookupResponse {
  magic_link_token: string;
  public_job_id: string;
}

export interface GeocodeResponse {
  lat: number;
  lng: number;
  display: string;
}

export interface TrackingView {
  job_status: string;
  tracking_status?: string;
  eta_minutes?: number | null;
  distance_miles?: number | null;
  driver_lat?: number | null;
  driver_lng?: number | null;
  driver_location_captured_at?: string | null;
  mechanic_lat?: number | null;
  mechanic_lng?: number | null;
  mechanic_company?: string | null;
  mechanic_contact?: string | null;
  mechanic_address?: string | null;
  mechanic_city?: string | null;
  mechanic_state?: string | null;
  mechanic_last_updated?: string | null;
  driver_eta_decision?: string | null;
}

export interface MechanicOfferView {
  public_job_id: string;
  issue_type: string;
  issue_summary?: string | null;
  vehicle_type?: string | null;
  driver_area?: string | null;
  driver_lat?: number | null;
  driver_lng?: number | null;
  dispatch_attempt_id: string;
  dispatch_status: string;
  suggested_eta_minutes?: number | null;
  offer_state: string;
  job_filled: boolean;
}

export interface RematchCandidate {
  mechanic_id: string;
  company_name: string;
  contact_name: string;
  city?: string | null;
  state?: string | null;
  rating?: number | null;
  distance_miles?: number | null;
  estimated_eta_minutes?: number | null;
  rank_score: number;
  base_lat: number;
  base_lng: number;
}

export interface MechanicTrackingView {
  public_job_id: string;
  job_status: string;
  driver_name?: string | null;
  vehicle_type?: string | null;
  issue_type?: string | null;
  issue_summary?: string | null;
  driver_lat?: number | null;
  driver_lng?: number | null;
  driver_location_captured_at?: string | null;
  mechanic_lat?: number | null;
  mechanic_lng?: number | null;
  mechanic_company?: string | null;
  mechanic_contact?: string | null;
  eta_minutes?: number | null;
  distance_miles?: number | null;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
}

export interface ConfirmPaymentResponse {
  success: boolean;
  status?: string;
}

export async function getJobByToken(token: string): Promise<JobDriverView> {
  return request<JobDriverView>(`/jobs/${token}`);
}

export async function getJobByCode(code: string): Promise<JobCodeLookupResponse> {
  return request<JobCodeLookupResponse>(`/jobs/by-code/${encodeURIComponent(code)}`);
}

export async function updateDriverLocation(
  token: string,
  lat: number,
  lng: number
): Promise<LocationUpdateResponse> {
  return request<LocationUpdateResponse>(`/jobs/${token}/location`, {
    method: "POST",
    body: JSON.stringify({ lat, lng }),
  });
}

export async function geocodeAddress(body: {
  address?: string;
  city?: string;
  state?: string;
}): Promise<GeocodeResponse> {
  return request<GeocodeResponse>("/jobs/geocode", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function createPaymentIntent(
  token: string
): Promise<PaymentIntentResponse> {
  return request<PaymentIntentResponse>(`/jobs/${token}/payment-intent`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function confirmPayment(
  token: string,
  payment_intent_id: string
): Promise<ConfirmPaymentResponse> {
  return request<ConfirmPaymentResponse>(`/jobs/${token}/payment-confirm`, {
    method: "POST",
    body: JSON.stringify({ payment_intent_id }),
  });
}

export async function getJobStatus(token: string): Promise<JobDriverView> {
  return request<JobDriverView>(`/jobs/${token}/status`);
}

export async function getTracking(token: string): Promise<TrackingView> {
  return request<TrackingView>(`/jobs/${token}/tracking`);
}

export async function getMechanicTracking(
  token: string
): Promise<MechanicTrackingView> {
  return request<MechanicTrackingView>(`/jobs/mechanic-tracking/${token}`);
}

export async function getMechanicOffer(token: string): Promise<MechanicOfferView> {
  return request<MechanicOfferView>(`/dispatch/mechanic-offer/${encodeURIComponent(token)}`);
}

export async function getMechanicOfferStatus(token: string): Promise<{
  offer_state: string;
  job_filled: boolean;
  dispatch_status: string;
  public_job_id: string;
}> {
  return request(`/dispatch/mechanic-offer/${encodeURIComponent(token)}/status`);
}

export async function respondMechanicOffer(
  token: string,
  body: { response: string; eta_minutes?: number | null; notes?: string | null }
): Promise<{ success: boolean; dispatch_status: string; job_status: string }> {
  return request(`/dispatch/mechanic-offer/${encodeURIComponent(token)}/respond`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchDriverEta(
  token: string,
  decision: "accepted" | "rejected"
): Promise<JobDriverView> {
  return request<JobDriverView>(`/jobs/${encodeURIComponent(token)}/driver-eta`, {
    method: "PATCH",
    body: JSON.stringify({ decision }),
  });
}

export async function getRematchCandidates(
  token: string,
  limit = 15
): Promise<RematchCandidate[]> {
  const q = new URLSearchParams({ limit: String(limit) });
  return request<RematchCandidate[]>(
    `/jobs/${encodeURIComponent(token)}/rematch-candidates?${q.toString()}`
  );
}

export async function selectRematchMechanic(
  token: string,
  mechanicId: string
): Promise<JobDriverView> {
  return request<JobDriverView>(`/jobs/${encodeURIComponent(token)}/rematch-select`, {
    method: "POST",
    body: JSON.stringify({ mechanic_id: mechanicId }),
  });
}
