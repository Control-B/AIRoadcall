import Link from "next/link";
import { PageLayout } from "@/components/page-layout";

const sections = [
  {
    title: "1. Acceptance of Terms",
    body: [
      "These Terms of Use govern your access to and use of Roadcall.ai, a roadside assistance connection and dispatch platform operated by Omniweb, LLC. By accessing, calling, messaging, or using Roadcall.ai, you agree to be bound by these Terms and our Privacy Policy.",
      "If you are using Roadcall.ai on behalf of a company, fleet, repair shop, or other organization, you represent that you have authority to bind that organization to these Terms.",
    ],
  },
  {
    title: "2. What Roadcall.ai Provides",
    body: [
      "Roadcall.ai helps connect drivers, vehicle owners, fleet operators, and other users seeking roadside help with independent mechanics, tow providers, mobile repair providers, and related service providers.",
      "Roadcall.ai may use automated systems, voice agents, text messaging, location links, scoring systems, dispatch logic, and live tracking tools to facilitate these connections. Roadcall.ai is a technology platform and dispatch facilitation service; unless expressly stated otherwise, Roadcall.ai does not itself perform towing, roadside repair, vehicle transport, locksmith work, jump starts, tire repair, fuel delivery, or other field services.",
    ],
  },
  {
    title: "3. No Guarantee of Availability or Outcomes",
    body: [
      "Roadcall.ai does not guarantee that a mechanic or service provider will be available, will accept a dispatch, will arrive within a specific timeframe, or will resolve a vehicle issue successfully.",
      "Estimated arrival times, ranking results, provider availability, ratings, and suggested matches are informational estimates only. Actual availability, pricing, qualifications, travel time, and service quality may vary.",
    ],
  },
  {
    title: "4. Independent Service Providers",
    body: [
      "Mechanics, tow operators, roadside vendors, and other providers available through Roadcall.ai are generally independent third parties and are not employees, agents, partners, joint venturers, or franchisees of Omniweb, LLC unless explicitly identified otherwise in writing.",
      "You acknowledge that any in-person service, repair, tow, recovery, lockout, tire assistance, fuel delivery, or other roadside work is performed by the third-party provider you select or are connected with, and that provider is solely responsible for its own conduct, representations, licensing, insurance, workmanship, safety practices, and compliance with applicable law.",
    ],
  },
  {
    title: "5. Eligibility and Use Restrictions",
    body: [
      "You may use Roadcall.ai only if you can form a binding contract and only for lawful purposes. You agree not to use the service to submit false requests, impersonate others, abuse service providers, interfere with dispatch operations, scrape or reverse engineer the platform, or use automated means to overload or disrupt the system.",
      "You also agree not to use Roadcall.ai in connection with emergencies that require police, fire, ambulance, or other government emergency response. If there is an immediate danger to life, health, or safety, call 911 or your local emergency services immediately.",
    ],
  },
  {
    title: "6. Driver Information and Location Data",
    body: [
      "To connect you with roadside assistance, Roadcall.ai may ask for vehicle details, issue details, phone number, rough location, precise GPS location, and related dispatch information. If you receive a location-sharing link, you are responsible for reviewing the request before sharing your location.",
      "You represent that information you provide is accurate to the best of your knowledge. Inaccurate or incomplete information may delay service, reduce match quality, or prevent a successful dispatch.",
    ],
  },
  {
    title: "7. Calls, Messages, and Automated Communications",
    body: [
      "By using Roadcall.ai, you consent to receive calls, SMS messages, and other communications from Roadcall.ai and from independent service providers involved in your request, including automated or AI-assisted communications where permitted by law.",
      "Standard carrier messaging and data rates may apply. You are responsible for any fees charged by your carrier or service plan.",
    ],
  },
  {
    title: "8. Pricing, Payment Holds, and Charges",
    body: [
      "Roadcall.ai may present or facilitate pricing information, payment authorizations, deposit holds, cancellation charges, or related payment workflows. A price quote or hold authorization does not guarantee the final total owed to a provider unless explicitly stated.",
      "You authorize applicable payment holds or charges that you approve through the Roadcall.ai flow. Additional charges may apply based on actual services rendered, travel distance, parts, labor, vehicle condition, time of day, or other provider-specific factors. Final pricing may be set by the independent provider unless otherwise stated.",
    ],
  },
  {
    title: "9. Cancellations and No-Shows",
    body: [
      "If you cancel a request after a provider has been dispatched or is en route, a cancellation fee may apply. If a provider arrives and cannot perform work due to inaccurate information, unsafe conditions, inaccessible vehicles, nonpayment, or customer unavailability, additional fees may apply.",
    ],
  },
  {
    title: "10. Safety and Vehicle Responsibility",
    body: [
      "You are responsible for keeping yourself, your passengers, and your vehicle in a reasonably safe location while waiting for assistance. Roadcall.ai does not control road conditions, traffic, weather, vehicle condition, or provider conduct.",
      "Do not rely on Roadcall.ai for emergency rescue or medical response. If a vehicle is in an unsafe position or if anyone may be injured, contact emergency services first.",
    ],
  },
  {
    title: "11. Service Limitations and Disclaimers",
    body: [
      "ROADCALL.AI IS PROVIDED ON AN \"AS IS\" AND \"AS AVAILABLE\" BASIS. TO THE MAXIMUM EXTENT PERMITTED BY LAW, OMNIWEB, LLC DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, NON-INFRINGEMENT, ACCURACY, AVAILABILITY, AND QUIET ENJOYMENT.",
      "We do not warrant that the platform will be uninterrupted, error-free, secure, or always available, or that any provider listing, ETA, ranking, transcript, summary, route, price, or match will be complete, accurate, or current.",
    ],
  },
  {
    title: "12. Limitation of Liability",
    body: [
      "To the fullest extent permitted by law, Omniweb, LLC, Roadcall.ai, and their officers, directors, employees, contractors, licensors, and affiliates will not be liable for any indirect, incidental, special, consequential, exemplary, or punitive damages, or for any loss of profits, revenue, goodwill, data, business opportunity, or vehicle use, arising from or related to your use of or inability to use the service.",
      "To the fullest extent permitted by law, the total aggregate liability of Omniweb, LLC and Roadcall.ai for any claim arising out of or relating to the service will not exceed the greater of: (a) the amount you paid directly to Roadcall.ai in the three months preceding the event giving rise to the claim, or (b) one hundred U.S. dollars (US$100).",
    ],
  },
  {
    title: "13. Indemnification",
    body: [
      "You agree to defend, indemnify, and hold harmless Omniweb, LLC, Roadcall.ai, and their affiliates, personnel, and service providers from and against any claims, damages, liabilities, losses, costs, and expenses, including reasonable attorneys' fees, arising out of or related to your use of the service, your violation of these Terms, your misuse of location or payment tools, or your interactions with third-party providers.",
    ],
  },
  {
    title: "14. Intellectual Property",
    body: [
      "Roadcall.ai, including its software, dispatch logic, AI workflows, content, trademarks, logos, visual design, and related materials, is owned by Omniweb, LLC or its licensors and is protected by applicable intellectual property laws. Except for limited rights to use the service under these Terms, no rights are granted to you.",
    ],
  },
  {
    title: "15. Suspension and Termination",
    body: [
      "We may suspend, restrict, or terminate access to Roadcall.ai at any time, with or without notice, if we believe you have violated these Terms, created risk, misused the service, attempted fraud, or interfered with operations.",
    ],
  },
  {
    title: "16. Governing Law",
    body: [
      "These Terms are governed by the laws of the State of Florida, without regard to conflict-of-law principles, except to the extent otherwise required by applicable law. You agree that any dispute arising out of or related to these Terms or the service will be brought in the state or federal courts located in Florida, and you consent to personal jurisdiction and venue there, unless applicable law requires otherwise.",
    ],
  },
  {
    title: "17. Changes to Terms",
    body: [
      "We may update these Terms from time to time. The updated version will be posted on this page with a revised effective date. Your continued use of Roadcall.ai after changes become effective constitutes your acceptance of the revised Terms.",
    ],
  },
  {
    title: "18. Contact Information",
    body: [
      "If you have questions about these Terms, contact Omniweb, LLC at support@roadcall.ai.",
    ],
  },
];

function LegalSection({ title, body }: { title: string; body: string[] }) {
  return (
    <section className="border-t border-white/10 py-8 first:border-t-0 first:pt-0">
      <h2 className="text-2xl font-semibold tracking-tight text-white">{title}</h2>
      <div className="mt-4 space-y-4 text-sm leading-7 text-slate-300 md:text-base">
        {body.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </section>
  );
}

export default function TermsPage() {
  return (
    <PageLayout>
      <section className="pt-28 pb-20 md:pt-36 md:pb-28">
        <div className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl shadow-black/20 backdrop-blur-sm md:p-12">
            <div className="mb-10">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-orange-400">
                Legal
              </p>
              <h1 className="mt-4 text-4xl font-bold tracking-tight text-white md:text-5xl">
                Terms of Use
              </h1>
              <p className="mt-4 text-sm text-slate-400 md:text-base">
                Effective Date: April 17, 2026
              </p>
              <p className="mt-6 max-w-3xl text-base leading-7 text-slate-300 md:text-lg">
                These Terms of Use govern how drivers, mechanics, fleet operators, and other users may access and use Roadcall.ai. Roadcall.ai helps connect drivers with independent roadside service providers through voice, SMS, dispatch, location-sharing, and tracking tools.
              </p>
            </div>

            <div className="space-y-2 rounded-2xl border border-orange-500/20 bg-orange-500/10 p-5 text-sm text-orange-100">
              <p>
                <strong>Important:</strong> Roadcall.ai is not a replacement for emergency services. If there is an immediate emergency or risk of injury, call <strong>911</strong> or your local emergency services first.
              </p>
            </div>

            <div className="mt-10 space-y-2">
              {sections.map((section) => (
                <LegalSection key={section.title} title={section.title} body={section.body} />
              ))}
            </div>

            <div className="mt-12 rounded-2xl border border-white/10 bg-[#0b1220] p-6 text-sm text-slate-300">
              <p>
                For questions about these Terms, email <a className="text-orange-300 hover:text-orange-200" href="mailto:support@roadcall.ai">support@roadcall.ai</a> or visit the <Link className="text-orange-300 hover:text-orange-200" href="/company">Company</Link> page.
              </p>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
