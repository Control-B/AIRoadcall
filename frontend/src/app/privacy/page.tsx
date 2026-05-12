import Link from "next/link";
import { PageLayout } from "@/components/page-layout";

const sections = [
  {
    title: "1. Overview",
    body: [
      "This Privacy Policy explains how Omniweb, LLC collects, uses, stores, and shares information when you use Roadcall.ai. Roadcall.ai is a roadside dispatch and connection platform that helps connect drivers and vehicle owners with independent mechanics and roadside service providers.",
      "This Policy applies to our website, phone experiences, AI voice agents, SMS messages, magic-link pages, live tracking tools, dashboards, and related services.",
    ],
  },
  {
    title: "2. Information We Collect",
    body: [
      "We may collect contact information such as your name, phone number, email address, and company name. We may collect request data such as vehicle type, roadside issue, rough location, exact GPS location, job status, ETA information, provider details, and payment-related workflow information.",
      "We may also collect call-related information such as audio, call recordings where permitted by law, call summaries, transcripts, AI-generated notes, dispatch outcomes, provider response details, and conversation history or memory notes associated with a caller or mechanic phone number.",
    ],
  },
  {
    title: "3. Location Information",
    body: [
      "If you use a magic link or location-sharing feature, we may collect precise geolocation information from your browser or device with your permission. We may also collect rough location details that you provide verbally or by text, such as city, state, highway, or nearby landmarks.",
      "We use location information to match drivers with nearby service providers, improve dispatch accuracy, estimate travel times, and support live tracking views for drivers and service providers.",
    ],
  },
  {
    title: "4. Call Audio, Transcripts, and AI Memory",
    body: [
      "Roadcall.ai may process call audio, generate transcripts, create summaries, and store conversation memory to improve continuity, including remembering prior dispatch context or name pronunciations. We may also store mechanic-specific interaction notes, such as prior acceptance patterns or ETA responses, to improve future dispatch quality.",
      "We use this information to operate the service, improve matching and routing, support quality review, investigate issues, and provide better future interactions.",
    ],
  },
  {
    title: "5. SMS and Messaging",
    body: [
      "We may send text messages such as magic links, dispatch updates, ETA notifications, or other service-related messages. Standard carrier messaging and data rates may apply. We use third-party messaging providers, including Twilio or similar providers, to deliver messages.",
    ],
  },
  {
    title: "6. Payment Information",
    body: [
      "Roadcall.ai may facilitate payment holds, payment authorizations, or related checkout workflows. Payment card details are processed by our payment providers, such as Stripe, and are not stored by us except for limited metadata, tokens, status information, or transaction references necessary to support the service.",
    ],
  },
  {
    title: "7. How We Use Information",
    body: [
      "We use personal information to operate Roadcall.ai, respond to requests, connect drivers with providers, send SMS links and updates, improve dispatch logic, maintain caller and mechanic memory, provide maps and ETA estimates, process payments, prevent fraud or misuse, comply with legal obligations, and improve the quality and safety of our platform.",
    ],
  },
  {
    title: "8. How We Share Information",
    body: [
      "We may share relevant information with independent mechanics, tow operators, and other service providers so they can evaluate, accept, travel to, and complete a job. This may include your first name, callback number, vehicle type, roadside issue, rough or exact location, and ETA/tracking data as needed.",
      "We may also share information with service providers that support our platform, such as cloud hosting, telephony, AI, mapping, analytics, messaging, and payment vendors. We may disclose information when required by law, legal process, or to protect rights, safety, or property.",
    ],
  },
  {
    title: "9. Cookies, Logs, and Analytics",
    body: [
      "Our website and magic-link pages may use cookies, local storage, session data, server logs, and analytics tools to maintain sessions, improve reliability, understand usage, and support fraud prevention and performance monitoring.",
    ],
  },
  {
    title: "10. Data Retention",
    body: [
      "We retain information for as long as reasonably necessary to provide the service, maintain operational records, support dispute resolution, improve system performance, comply with legal obligations, and preserve safety or fraud-prevention records. Retention periods may vary depending on the category of data and legal requirements.",
    ],
  },
  {
    title: "11. Your Choices and Rights",
    body: [
      "Depending on your location and applicable law, you may have rights to request access to, correction of, or deletion of certain personal information, or to object to or limit certain processing. You may also request information about our data practices.",
      "To exercise a privacy request, contact us at support@roadcall.ai. We may need to verify your identity before responding.",
    ],
  },
  {
    title: "12. Security",
    body: [
      "We use reasonable administrative, technical, and organizational measures to protect personal information. However, no transmission or storage system is guaranteed to be completely secure, and we cannot guarantee absolute security.",
    ],
  },
  {
    title: "13. Children’s Privacy",
    body: [
      "Roadcall.ai is not directed to children under 13, and we do not knowingly collect personal information from children under 13 through the service. If you believe a child has provided information to us, contact us so we can review and address the situation.",
    ],
  },
  {
    title: "14. International Users",
    body: [
      "Roadcall.ai is operated in the United States and is intended primarily for U.S.-based dispatch operations. If you access the service from outside the United States, you understand that your information may be processed and stored in the United States and other jurisdictions where our providers operate.",
    ],
  },
  {
    title: "15. Changes to This Policy",
    body: [
      "We may update this Privacy Policy from time to time. When we do, we will update the effective date on this page. Your continued use of the service after changes become effective means the updated Policy will apply going forward.",
    ],
  },
  {
    title: "16. Contact Us",
    body: [
      "If you have questions about this Privacy Policy or our data practices, contact Omniweb, LLC at support@roadcall.ai.",
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

export default function PrivacyPage() {
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
                Privacy Policy
              </h1>
              <p className="mt-4 text-sm text-roadcall-muted md:text-base">
                Effective Date: April 17, 2026
              </p>
              <p className="mt-6 max-w-3xl text-base leading-7 text-roadcall-silver/85 md:text-lg">
                This Privacy Policy explains how Roadcall.ai collects, uses, stores, and shares information in connection with roadside dispatch, mechanic matching, location sharing, live tracking, and related communications.
              </p>
            </div>

            <div className="space-y-2 rounded-2xl border border-blue-500/20 bg-blue-500/10 p-5 text-sm text-blue-100">
              <p>
                We designed Roadcall.ai to use data for one main purpose: helping connect drivers with roadside service providers quickly, safely, and accurately.
              </p>
            </div>

            <div className="mt-10 space-y-2">
              {sections.map((section) => (
                <LegalSection key={section.title} title={section.title} body={section.body} />
              ))}
            </div>

            <div className="mt-12 rounded-2xl border border-roadcall-cyan/10 bg-[#0b1220] p-6 text-sm text-roadcall-silver/85">
              <p>
                To ask a privacy question or submit a request, contact <a className="text-roadcall-orange hover:text-roadcall-orange" href="mailto:support@roadcall.ai">support@roadcall.ai</a> or visit the <Link className="text-roadcall-orange hover:text-roadcall-orange" href="/company">Company</Link> page.
              </p>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
