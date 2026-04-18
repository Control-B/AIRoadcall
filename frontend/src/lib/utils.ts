import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatIssueType(issueType: string): string {
  if (!issueType) return "Unknown issue";
  return issueType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function getStatusStep(status: string): number {
  switch (status) {
    case "pending":
    case "intake_complete":
      return 1;
    case "awaiting_driver_location":
    case "awaiting_location":
      return 2;
    case "location_received":
    case "awaiting_payment_authorization":
      return 3;
    case "payment_authorized":
    case "matching_mechanics":
    case "calling_mechanics":
      return 4;
    case "mechanic_assigned":
    case "mechanic_en_route":
    case "mechanic_arrived":
    case "completed":
      return 5;
    default:
      return 1;
  }
}
