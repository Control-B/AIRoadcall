import { AlertTriangle } from "lucide-react";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="text-center space-y-4">
        <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto" />
        <h1 className="text-2xl font-bold">AI Roadside Support</h1>
        <p className="text-muted-foreground max-w-md">
          This page is accessed via a secure magic link sent to your phone after
          calling our AI roadside assistance line.
        </p>
        <p className="text-sm text-muted-foreground">
          If you need roadside help, please call our support line to get started.
        </p>
      </div>
    </div>
  );
}
