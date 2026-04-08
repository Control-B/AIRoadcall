const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface ApiErrorBody {
  detail?: string | { message?: string } | Array<{ msg?: string }>;
  message?: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
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
}

export interface JobDriverView {
  public_job_id: string;
  status: string;
  payment_status?: string | null;
  driver_name: string;
  issue_type: string;
  issue_summary?: string | null;
  vehicle_type?: string | null;
  driver_lat?: number | null;
  driver_lng?: number | null;
  payment_hold_amount: number | null;
  assigned_mechanic?: AssignedMechanic | null;
}

export interface TrackingView {
  job_status: string;
  tracking_status?: string;
  eta_minutes?: number | null;
  driver_lat?: number | null;
  driver_lng?: number | null;
  mechanic_lat?: number | null;
  mechanic_lng?: number | null;
  mechanic_company?: string | null;
  mechanic_contact?: string | null;
  mechanic_last_updated?: string | null;
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

export async function updateDriverLocation(
  token: string,
  lat: number,
  lng: number
): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/jobs/${token}/location`, {
    method: "POST",
    body: JSON.stringify({ lat, lng }),
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
