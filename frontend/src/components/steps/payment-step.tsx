"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { stripePromise } from "@/lib/stripe";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  createPaymentIntent,
  confirmPayment,
} from "@/lib/api-client";
import {
  CreditCard,
  Loader2,
  Shield,
  CheckCircle2,
  XCircle,
} from "lucide-react";

interface PaymentStepProps {
  token: string;
  holdAmount: number | null;
  onSuccess: () => void;
}

export function PaymentStep({ token, holdAmount, onSuccess }: PaymentStepProps) {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentIntentId, setPaymentIntentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const initPayment = async () => {
      try {
        const result = await createPaymentIntent(token);
        setClientSecret(result.client_secret);
        setPaymentIntentId(result.payment_intent_id);
      } catch (err: any) {
        setError(err.message || "Failed to initialize payment");
      } finally {
        setLoading(false);
      }
    };

    initPayment();
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-purple-100">
            <CreditCard className="h-8 w-8 text-purple-600" />
          </div>
          <h2 className="text-2xl font-bold">Payment Authorization</h2>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center py-10">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="font-medium">Preparing secure payment...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Payment Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!clientSecret || !paymentIntentId) return null;

  return (
    <Elements
      stripe={stripePromise}
      options={{
        clientSecret,
        appearance: {
          theme: "stripe",
          variables: {
            colorPrimary: "#2563eb",
            borderRadius: "8px",
          },
        },
      }}
    >
      <PaymentForm
        token={token}
        paymentIntentId={paymentIntentId}
        holdAmount={holdAmount}
        onSuccess={onSuccess}
      />
    </Elements>
  );
}

function PaymentForm({
  token,
  paymentIntentId,
  holdAmount,
  onSuccess,
}: {
  token: string;
  paymentIntentId: string;
  holdAmount: number | null;
  onSuccess: () => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!stripe || !elements) return;

      setSubmitting(true);
      setError("");

      try {
        const { error: stripeError } = await stripe.confirmPayment({
          elements,
          confirmParams: {
            return_url: window.location.href,
          },
          redirect: "if_required",
        });

        if (stripeError) {
          setError(
            stripeError.message || "Payment authorization failed"
          );
          setSubmitting(false);
          return;
        }

        // Confirm with our backend
        const result = await confirmPayment(token, paymentIntentId);
        if (result.success) {
          setSuccess(true);
          setTimeout(() => onSuccess(), 1500);
        } else {
          setError("Payment authorization could not be confirmed");
        }
      } catch (err: any) {
        setError(err.message || "An unexpected error occurred");
      } finally {
        setSubmitting(false);
      }
    },
    [stripe, elements, token, paymentIntentId, onSuccess]
  );

  if (success) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-green-700">
            Payment Authorized
          </h2>
          <p className="mt-2 text-muted-foreground">
            Finding you a mechanic now...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-purple-100">
          <CreditCard className="h-8 w-8 text-purple-600" />
        </div>
        <h2 className="text-2xl font-bold">Authorize Payment Hold</h2>
        <p className="mt-2 text-muted-foreground">
          A temporary hold of{" "}
          <strong className="text-foreground">
            ${holdAmount?.toFixed(2) || "150.00"}
          </strong>{" "}
          will be placed on your card
        </p>
      </div>

      <Alert>
        <Shield className="h-4 w-4" />
        <AlertDescription>
          This is an <strong>authorization hold only</strong> — your card will
          not be charged until the service is completed and confirmed. The hold
          may be adjusted based on actual service costs.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Payment Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <PaymentElement />

            {error && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button
              type="submit"
              size="xl"
              className="w-full"
              disabled={!stripe || !elements || submitting}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Authorizing...
                </>
              ) : (
                <>
                  <Shield className="mr-2 h-5 w-5" />
                  Authorize ${holdAmount?.toFixed(2) || "150.00"} Hold
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
