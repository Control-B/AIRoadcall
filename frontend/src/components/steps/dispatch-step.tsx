"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { getJobStatus, type JobDriverView } from "@/lib/api-client";
import { Loader2, Search, Phone, CheckCircle2, Wrench } from "lucide-react";

interface DispatchStepProps {
  token: string;
  onMechanicAssigned: (job: JobDriverView) => void;
}

const DISPATCH_STATUSES = [
  {
    status: "matching_mechanics",
    icon: Search,
    title: "Reviewing Nearby Providers",
    description: "We're identifying qualified mechanics in your area...",
    color: "text-blue-600",
    bgColor: "bg-blue-100",
  },
  {
    status: "calling_mechanics",
    icon: Phone,
    title: "Contacting Available Mechanics",
    description: "We're reaching out to mechanics who can help...",
    color: "text-amber-600",
    bgColor: "bg-amber-100",
  },
  {
    status: "mechanic_assigned",
    icon: CheckCircle2,
    title: "Mechanic Confirmed!",
    description: "A mechanic has accepted your job and is preparing to head your way.",
    color: "text-green-600",
    bgColor: "bg-green-100",
  },
];

export function DispatchStep({ token, onMechanicAssigned }: DispatchStepProps) {
  const [currentStatus, setCurrentStatus] = useState("matching_mechanics");
  const [job, setJob] = useState<JobDriverView | null>(null);

  const pollStatus = useCallback(async () => {
    try {
      const data = await getJobStatus(token);
      setJob(data);
      setCurrentStatus(data.status);

      if (
        data.status === "mechanic_assigned" ||
        data.status === "mechanic_en_route" ||
        data.status === "mechanic_arrived"
      ) {
        onMechanicAssigned(data);
      }
    } catch (err) {
      // Silently retry
    }
  }, [token, onMechanicAssigned]);

  useEffect(() => {
    pollStatus();
    const interval = setInterval(pollStatus, 7000); // Poll every 7 seconds
    return () => clearInterval(interval);
  }, [pollStatus]);

  const statusConfig =
    DISPATCH_STATUSES.find((s) => s.status === currentStatus) ||
    DISPATCH_STATUSES[0];
  const Icon = statusConfig.icon;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div
          className={`mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full ${statusConfig.bgColor} relative`}
        >
          <Icon className={`h-10 w-10 ${statusConfig.color}`} />
          {currentStatus !== "mechanic_assigned" && (
            <div className="absolute inset-0 rounded-full border-4 border-primary/30 animate-pulse-ring" />
          )}
        </div>
        <h2 className="text-2xl font-bold">{statusConfig.title}</h2>
        <p className="mt-2 text-muted-foreground">
          {statusConfig.description}
        </p>
      </div>

      {currentStatus !== "mechanic_assigned" && (
        <Card>
          <CardContent className="py-6">
            <div className="flex items-center justify-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">
                Checking for updates...
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {job?.assigned_mechanic && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <Wrench className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="font-semibold">
                  {job.assigned_mechanic.company_name}
                </p>
                <p className="text-sm text-muted-foreground">
                  {job.assigned_mechanic.contact_name}
                </p>
                {job.assigned_mechanic.eta_minutes && (
                  <p className="text-sm font-medium text-green-700">
                    ETA: ~{job.assigned_mechanic.eta_minutes} min
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Alert>
        <AlertDescription className="text-center">
          Please stay with your vehicle. We&apos;ll notify you as soon as a
          mechanic is on the way.
        </AlertDescription>
      </Alert>
    </div>
  );
}
