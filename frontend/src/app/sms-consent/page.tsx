import Link from "next/link";
import { PageLayout } from "@/components/page-layout";

const sections = [
  {
    title: "1. How Users Opt In",
    body: [
      "Users may opt in to receive SMS messages from Omniweb and Roadcall.ai by initiating contact through our AI phone system, submitting forms on our websites, engaging with AI assistants and requesting follow-up communication, or otherwise providing express consent to receive service-related text messages.",
      "Consent to receive SMS messages is not a condition of purchase. Message consent applies only to the phone number provided and only for the purposes described in this policy.",
    ],
  },
  {
    title: "2. Types of Messages",
    body: [
      "If you opt in, you may receive customer support messages, roadside dispatch updates, service-related notifications, magic-link messages for location sharing, ETA and tracking messages, appointment or follow-up notifications, and limited account or operational alerts related to the services you requested.",
      "We do not use SMS consent for unrelated third-party marketing. If we ever offer promotional SMS programs, they will be governed by separate consent language where required.",
    ],
  },
  {
    title: "3. Message Frequency",
    body: [
      "Message frequency may vary depending on your interaction with Omniweb or Roadcall.ai. For roadside use cases, you may receive a small series of messages tied to a specific active service request, such as a magic link, status update, or ETA update.",
    ],
  },
  {
    title: "4. Message and Data Rates",
    body: [
      "Message and data rates may apply according to your mobile carrier plan. Omniweb is not responsible for SMS or data charges imposed by your wireless carrier.",
    ],
  },
  {
    title: "5. STOP and HELP Instructions",
    body: [
      "You may opt out of non-essential SMS messages at any time by replying STOP to a message you receive from us, where applicable. After you send STOP, we may send a final confirmation message confirming your opt-out.",
      "For help, reply HELP where supported, or contact us at support@roadcall.ai. Some transactional or operational communications that are strictly necessary to complete an active roadside request may still be sent where permitted by law.",
    ],
  },
  {
    title: "6. Consent Records",
    body: [
      "We may maintain records of when and how consent was obtained, including form submissions, inbound calls, AI conversation logs, timestamps, message records, and related operational metadata. These records help us demonstrate compliance with applicable regulations and carrier requirements.",
    ],
  },
  {
    title: "7. Carriers and Delivery",
    body: [
      "Wireless carriers are not liable for delayed or undelivered messages. Delivery is subject to effective transmission by your carrier, network availability, routing conditions, and device capability.",
    ],
  },
  {
    title: "8. Privacy and Data Use",
    body: [
      "Information collected through SMS interactions may be used to provide support, operate roadside dispatch, verify requests, improve system quality, and maintain communication history. SMS data is also subject to our Privacy Policy.",
      "We do not sell your SMS consent or phone number as part of a consumer marketing list. We may use authorized communications providers to deliver messages on our behalf.",
    ],
  },
  {
    title: "9. Eligibility and Authorized Use",
    body: [
      "By opting in, you represent that you are the subscriber or customary user of the mobile number provided, or that you are authorized to provide consent for that number. You agree not to provide a number that you do not control or have permission to use for service communications.",
    ],
  },
  {
    title: "10. Changes to This Policy",
    body: [
      "We may update this SMS Consent Policy from time to time. The updated version will be posted on this page with a revised effective date. Your continued interaction with our services after changes become effective constitutes acknowledgement of the revised policy to the extent permitted by law.",
    ],
  },
  {
    title: "11. Contact Information",
    body: [
      "If you have questions about this SMS Consent Policy, contact Omniweb, LLC at support@roadcall.ai.",
    ],
  },
];

function LegalSection({ title, body }: { title: string; body: string[] }) {
  return (
    <section className="border-t border-roadcall-cyan/10 py-8 first:border-t-0 first:pt-0">
      <h2 className="text-2xl font-semibold tracking-tight text-white">{title}</h2>
      <div className="mt-4 space-y-4 text-sm leading-7 text-roadcall-silver/85 md:text-base">
        {body.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </section>
  );
}

export default function SmsConsentPage() {
  return (
    <PageLayout>
      <section className="pt-28 pb-20 md:pt-36 md:pb-28">
        <div className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="rounded-3xl border border-roadcall-cyan/10 bg-roadcall-panel/35 p-8 shadow-2xl shadow-black/20 backdrop-blur-sm md:p-12">
            <div className="mb-10">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-roadcall-orange">
                Legal
              </p>
              <h1 className="mt-4 text-4xl font-bold tracking-tight text-white md:text-5xl">
                SMS Consent Policy
              </h1>
              <p className="mt-4 text-sm text-roadcall-muted md:text-base">
                Effective Date: April 10, 2026
              </p>
              <p className="mt-6 max-w-3xl text-base leading-7 text-roadcall-silver/85 md:text-lg">
                Omniweb, LLC provides AI-powered communication services, including SMS notifications and messaging for Roadcall.ai and related service workflows. This policy explains how consent for SMS communications is collected and used in accordance with applicable legal and carrier requirements, including TCPA and CTIA guidelines.
              </p>
            </div>

            <div className="space-y-2 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-5 text-sm text-emerald-100">
              <p>
                SMS consent is collected only for service-related communication workflows. Consent is <strong>not</strong> a condition of purchase.
              </p>
            </div>

            <div className="mt-10 space-y-2">
              {sections.map((section) => (
                <LegalSection key={section.title} title={section.title} body={section.body} />
              ))}
            </div>

            <div className="mt-12 rounded-2xl border border-roadcall-cyan/10 bg-[#0b1220] p-6 text-sm text-roadcall-silver/85">
              <p>
                You can also review our <Link className="text-roadcall-orange hover:text-roadcall-orange" href="/privacy">Privacy Policy</Link> and <Link className="text-roadcall-orange hover:text-roadcall-orange" href="/terms">Terms of Use</Link> for related information about communications, data handling, and service limitations.
              </p>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
