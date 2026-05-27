import { redirect } from "next/navigation";
import { supportMailtoHref } from "@/lib/support-email";

export default function ProviderRegisterPage() {
  redirect(supportMailtoHref("Roadcall shop listing request", { source: "provider_register" }));
}
