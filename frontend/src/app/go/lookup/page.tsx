"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, MapPin } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function normalizeCaseCode(raw: string): string {
  const cleaned = raw.toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (!cleaned) {
    return "";
  }

  const withoutPrefix = cleaned.startsWith("RC") ? cleaned.slice(2) : cleaned;
  if (!withoutPrefix) {
    return "RC-";
  }

  return `RC-${withoutPrefix}`;
}

export default function GoEntryPage() {
  const router = useRouter();
  const [codeInput, setCodeInput] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const normalizedPreview = useMemo(() => normalizeCaseCode(codeInput), [codeInput]);

  function handleChange(value: string) {
    setCodeInput(value);
    if (error) {
      setError("");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedCode = normalizeCaseCode(codeInput);
    const isValid = /^RC-[A-Z0-9]{4,12}$/.test(normalizedCode);

    if (!isValid) {
      setError("Enter the case code exactly as Roadcall gave it to you.");
      return;
    }

    setSubmitting(true);
    router.push(`/go/${normalizedCode}`);
  }

  return (
    <div className="min-h-screen bg-background px-4 py-10 text-foreground">
      <div className="mx-auto max-w-md">
        <Card className="border-border/80 shadow-xl">
          <CardHeader className="space-y-4 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <MapPin className="h-8 w-8 text-primary" />
            </div>
            <div className="space-y-2">
              <CardTitle className="text-3xl">Find your roadside case</CardTitle>
              <CardDescription className="text-sm leading-6">
                Enter the case code the agent gave you to open your Roadcall link,
                share your exact location, and track your mechanic.
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="case-code" className="text-sm font-medium">
                  Case code
                </label>
                <Input
                  id="case-code"
                  value={codeInput}
                  onChange={(event) => handleChange(event.target.value)}
                  placeholder="RC-1234ABCD"
                  autoCapitalize="characters"
                  autoCorrect="off"
                  spellCheck={false}
                  inputMode="text"
                  className="h-14 text-center font-mono text-lg tracking-[0.2em] uppercase"
                />
                <p className="text-xs text-muted-foreground">
                  Example: <span className="font-mono">RC-A1B2C3D4</span>
                </p>
              </div>

              {normalizedPreview && normalizedPreview !== "RC-" && (
                <div className="rounded-lg border border-border bg-muted/40 px-4 py-3 text-center text-sm text-muted-foreground">
                  We&apos;ll look up: <span className="font-mono font-semibold text-foreground">{normalizedPreview}</span>
                </div>
              )}

              {error && (
                <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={submitting}
              >
                {submitting ? "Opening your case..." : "Open my case"}
                {!submitting && <ArrowRight className="ml-2 h-4 w-4" />}
              </Button>
            </form>

            <div className="mt-6 rounded-xl border border-border/70 bg-muted/30 p-4 text-sm text-muted-foreground">
              If you&apos;re on the phone with Roadcall, the agent can read your case code out loud.
              Once your page opens, you&apos;ll be able to confirm your location and follow your mechanic on the map.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}