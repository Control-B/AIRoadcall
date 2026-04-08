"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { formatIssueType } from "@/lib/utils";
import { MapPin, AlertTriangle, Car, User } from "lucide-react";
import type { JobDriverView } from "@/lib/api-client";

interface JobSummaryStepProps {
  job: JobDriverView;
  onContinue: () => void;
}

export function JobSummaryStep({ job, onContinue }: JobSummaryStepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-100">
          <AlertTriangle className="h-8 w-8 text-amber-600" />
        </div>
        <h2 className="text-2xl font-bold text-foreground">
          Roadside Assistance
        </h2>
        <p className="mt-2 text-muted-foreground">
          We&apos;re here to help you get back on the road
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Your Request Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <User className="h-5 w-5 text-muted-foreground flex-shrink-0" />
            <div>
              <p className="text-sm text-muted-foreground">Driver</p>
              <p className="font-medium">{job.driver_name}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
            <div>
              <p className="text-sm text-muted-foreground">Issue</p>
              <p className="font-medium">
                {formatIssueType(job.issue_type)}
              </p>
            </div>
          </div>

          {job.vehicle_type && (
            <div className="flex items-center gap-3">
              <Car className="h-5 w-5 text-muted-foreground flex-shrink-0" />
              <div>
                <p className="text-sm text-muted-foreground">Vehicle</p>
                <p className="font-medium capitalize">{job.vehicle_type}</p>
              </div>
            </div>
          )}

          {job.issue_summary && (
            <div className="rounded-lg bg-muted p-3">
              <p className="text-sm text-muted-foreground mb-1">Details</p>
              <p className="text-sm">{job.issue_summary}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Alert>
        <MapPin className="h-4 w-4" />
        <AlertDescription>
          To dispatch help, we need your <strong>exact location</strong> and a{" "}
          <strong>payment authorization hold</strong>. Your card will not be
          charged until service is complete.
        </AlertDescription>
      </Alert>

      <Button
        size="xl"
        className="w-full"
        onClick={onContinue}
      >
        <MapPin className="mr-2 h-5 w-5" />
        Share My Location
      </Button>
    </div>
  );
}
