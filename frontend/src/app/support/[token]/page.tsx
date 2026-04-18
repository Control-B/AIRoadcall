"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  getJobByToken,
  getJobStatus,
  type JobDriverView,
} from "@/lib/api-client";
import { getStatusStep } from "@/lib/utils";
import { StepIndicator } from "@/components/step-indicator";
import { JobSummaryStep } from "@/components/steps/job-summary-step";
import { LocationStep } from "@/components/steps/location-step";
import { PaymentStep } from "@/components/steps/payment-step";
import { DispatchStep } from "@/components/steps/dispatch-step";
import { TrackingStep } from "@/components/steps/tracking-step";
import { RematchStep } from "@/components/steps/rematch-step";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, ShieldAlert, Clock } from "lucide-react";

const STEPS = [
  { label: "Summary" },
  { label: "Location" },
  { label: "Payment" },
  { label: "Dispatch" },
  { label: "Tracking" },
];

export default function SupportPage() {
  const params = useParams();
  const token = params.token as string;

  const [job, setJob] = useState<JobDriverView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [currentStep, setCurrentStep] = useState(1);

  // Load job data on mount
  useEffect(() => {
    async function loadJob() {
      try {
        const data = await getJobByToken(token);
        setJob(data);

        // Determine which step to show based on job status
        const step = getStatusStep(data.status);
        if (step > 0) {
          setCurrentStep(step);
        }

        // If payment is authorized but not yet dispatching,
        // jump to dispatch step
        if (
          data.status === "payment_authorized" ||
          data.status === "matching_mechanics" ||
          data.status === "calling_mechanics"
        ) {
          setCurrentStep(4);
        }

        // If mechanic is assigned/en route/arrived, jump to tracking
        if (
          data.status === "mechanic_assigned" ||
          data.status === "mechanic_en_route" ||
          data.status === "mechanic_arrived"
        ) {
          setCurrentStep(5);
        }

        if (
          data.driver_eta_decision === "rejected" &&
          (data.status === "matching_mechanics" ||
            data.status === "calling_mechanics")
        ) {
          setCurrentStep(5);
        }
      } catch (err: any) {
        setError(err.message || "Unable to load your support request");
      } finally {
        setLoading(false);
      }
    }

    if (token) {
      loadJob();
    }
  }, [token]);

  // Handler: advance from summary to location
  const handleSummaryContinue = useCallback(() => {
    setCurrentStep(2);
  }, []);

  // Handler: location captured successfully
  const handleLocationSuccess = useCallback(
    async (lat: number, lng: number, status: string) => {
      const fallbackJob = job
        ? {
            ...job,
            driver_lat: lat,
            driver_lng: lng,
            status,
          }
        : null;

      try {
        const refreshedJob = await getJobStatus(token);
        setJob(refreshedJob);

        if (
          refreshedJob.status === "mechanic_assigned" ||
          refreshedJob.status === "mechanic_en_route" ||
          refreshedJob.status === "mechanic_arrived"
        ) {
          setCurrentStep(5);
          return;
        }

        if (
          refreshedJob.status === "matching_mechanics" ||
          refreshedJob.status === "calling_mechanics" ||
          refreshedJob.status === "payment_authorized"
        ) {
          setCurrentStep(4);
          return;
        }

        setCurrentStep(3);
      } catch {
        if (fallbackJob) {
          setJob(fallbackJob);
        }

        if (
          status === "mechanic_assigned" ||
          status === "mechanic_en_route" ||
          status === "mechanic_arrived"
        ) {
          setCurrentStep(5);
          return;
        }

        if (
          status === "matching_mechanics" ||
          status === "calling_mechanics" ||
          status === "payment_authorized"
        ) {
          setCurrentStep(4);
          return;
        }

        setCurrentStep(3);
      }
    },
    [job, token]
  );

  // Handler: payment authorized
  const handlePaymentSuccess = useCallback(() => {
    if (job) {
      setJob({
        ...job,
        payment_status: "authorized",
        status: "matching_mechanics",
      });
    }
    setCurrentStep(4);
  }, [job]);

  // Handler: mechanic assigned
  const handleMechanicAssigned = useCallback((updatedJob: JobDriverView) => {
    setJob(updatedJob);
    setCurrentStep(5);
  }, []);

  const handleJobUpdatedFromTracking = useCallback((updatedJob: JobDriverView) => {
    setJob(updatedJob);
    if (
      updatedJob.driver_eta_decision === "rejected" &&
      (updatedJob.status === "matching_mechanics" ||
        updatedJob.status === "calling_mechanics")
    ) {
      setCurrentStep(5);
    }
  }, []);

  const showRematch =
    job?.driver_eta_decision === "rejected" &&
    (job.status === "matching_mechanics" || job.status === "calling_mechanics");

  // Loading state
  if (loading) {
    return (
      <div className="mx-auto max-w-md p-4 pt-8 space-y-6">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-64 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="max-w-md space-y-6 text-center">
          <ShieldAlert className="h-16 w-16 text-destructive mx-auto" />
          <h2 className="text-2xl font-bold">Unable to Access</h2>
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Invalid or Expired Link</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <p className="text-sm text-muted-foreground">
            If you need roadside assistance, please call our support line for a
            new link.
          </p>
        </div>
      </div>
    );
  }

  // Canceled state
  if (job?.status === "canceled") {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="max-w-md space-y-4 text-center">
          <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto" />
          <h2 className="text-2xl font-bold">Request Canceled</h2>
          <p className="text-muted-foreground">
            This roadside assistance request has been canceled.
          </p>
        </div>
      </div>
    );
  }

  // Completed state
  if (job?.status === "completed") {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="max-w-md space-y-4 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <Clock className="h-8 w-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-green-700">
            Service Complete
          </h2>
          <p className="text-muted-foreground">
            Your roadside assistance has been completed. Thank you for using our
            service.
          </p>
        </div>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="mx-auto max-w-md px-4 py-6 pb-20">
      {/* Header */}
      <div className="mb-6 text-center">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          AI Roadside Support
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Ref: {job.public_job_id}
        </p>
      </div>

      {/* Step Indicator */}
      <div className="mb-8">
        <StepIndicator currentStep={currentStep} steps={STEPS} />
      </div>

      {/* Step Content */}
      <div className="animate-in fade-in duration-500">
        {currentStep === 1 && (
          <JobSummaryStep job={job} onContinue={handleSummaryContinue} />
        )}

        {currentStep === 2 && (
          <LocationStep token={token} onSuccess={handleLocationSuccess} />
        )}

        {currentStep === 3 && (
          <PaymentStep
            token={token}
            holdAmount={job.payment_hold_amount}
            onSuccess={handlePaymentSuccess}
          />
        )}

        {currentStep === 4 && (
          <DispatchStep
            token={token}
            onMechanicAssigned={handleMechanicAssigned}
          />
        )}

        {currentStep === 5 && showRematch ? (
          <RematchStep
            token={token}
            onOfferSent={(updated) => {
              setJob(updated);
              setCurrentStep(4);
            }}
          />
        ) : null}

        {currentStep === 5 && !showRematch ? (
          <TrackingStep
            token={token}
            mechanicCompany={job.assigned_mechanic?.company_name}
            mechanicContact={job.assigned_mechanic?.contact_name}
            onJobUpdated={handleJobUpdatedFromTracking}
          />
        ) : null}
      </div>
    </div>
  );
}
