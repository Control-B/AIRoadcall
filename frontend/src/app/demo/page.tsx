"use client";


import {
  Phone,
  MessageSquare,
  Clock,
  Users,
  TrendingUp,
  Shield,
  Zap,
  Star,
  ArrowRight,
  CheckCircle2,
  Headphones,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { HELP_PHONE, telHref } from "@/lib/phone";
import { STRIPE_PAYMENT_LINKS } from "@/lib/stripe-payment-links";

const features = [
  {
    icon: Phone,
    title: "24/7 AI Receptionist",
    description:
      "Never miss a call again. Your AI answers every call professionally, even at 3 AM.",
  },
  {
    icon: MessageSquare,
    title: "Text Chat Support",
    description:
      "Customers can text your business number and get instant AI-powered responses.",
  },
  {
    icon: Users,
    title: "Lead Qualification",
    description:
      "AI captures caller info, vehicle details, and service needs — scored and ready for follow-up.",
  },
  {
    icon: Clock,
    title: "Appointment Scheduling",
    description:
      "Callers can book appointments directly through the AI — syncs with your calendar.",
  },
  {
    icon: TrendingUp,
    title: "Call Analytics",
    description:
      "See every call, text, and lead in your dashboard. Know exactly what customers want.",
  },
  {
    icon: Shield,
    title: "Custom to Your Shop",
    description:
      "AI knows your services, hours, pricing, and speaks like a member of your team.",
  },
];

const plans = [
  {
    name: "Standard",
    price: 197,
    description: "Perfect for small shops",
    href: STRIPE_PAYMENT_LINKS.standard,
    features: [
      "AI phone receptionist",
      "Up to 200 calls/month",
      "Lead capture & scoring",
      "Call log dashboard",
      "Business hours routing",
      "Email support",
    ],
  },
  {
    name: "Professional",
    price: 297,
    description: "Most popular for busy shops",
    popular: true,
    href: STRIPE_PAYMENT_LINKS.professional,
    features: [
      "Everything in Standard",
      "Up to 1,000 calls/month",
      "Text chat support",
      "Appointment scheduling",
      "Custom AI voice",
      "Priority support",
      "Call forwarding to owner",
    ],
  },
  {
    name: "Premium",
    price: 497,
    description: "For multi-location operations",
    href: STRIPE_PAYMENT_LINKS.premium,
    features: [
      "Everything in Professional",
      "Unlimited calls",
      "Multi-location support",
      "Custom integrations",
      "Dedicated account manager",
      "API access",
      "White-label option",
    ],
  },
];

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Navbar */}
      <nav className="relative z-10 max-w-6xl mx-auto px-4 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Phone className="h-6 w-6 text-blue-400" />
          <span className="text-lg font-bold">AI Receptionist</span>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-600/20 via-transparent to-transparent" />
        <div className="relative max-w-6xl mx-auto px-4 pt-10 pb-24 text-center">
          <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-2 mb-8">
            <Zap className="h-4 w-4 text-blue-400" />
            <span className="text-sm text-blue-300">
              AI-Powered Phone System for Mechanic Shops
            </span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            Never Miss a
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              {" "}
              Customer Call
            </span>
            <br />
            Again
          </h1>

          <p className="text-xl text-roadcall-silver/85 max-w-2xl mx-auto mb-10">
            Your AI receptionist answers every call 24/7, qualifies leads,
            books appointments, and sounds like a real member of your team.
          </p>

          {/* Demo CTA */}
          <div className="bg-roadcall-panel/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-8 max-w-lg mx-auto mb-12">
            <div className="flex items-center justify-center gap-3 mb-4">
              <Headphones className="h-8 w-8 text-blue-400" />
              <h2 className="text-2xl font-bold">Try It Right Now</h2>
            </div>
            <p className="text-roadcall-silver/85 mb-6">
              Call our demo line and talk to the AI receptionist yourself.
              It&apos;s set up as a sample truck repair shop.
            </p>
            <a href={telHref(HELP_PHONE)}>
              <Button size="xl" className="w-full bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-xl gap-3">
                <Phone className="h-6 w-6" />
                {HELP_PHONE}
              </Button>
            </a>
            <p className="text-sm text-roadcall-muted mt-3">
              Free call · No signup required · Takes 60 seconds
            </p>
          </div>

          {/* Social proof */}
          <div className="flex items-center justify-center gap-8 text-roadcall-muted text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-400" />
              <span>35,000+ shops in our network</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-400" />
              <span>Setup in under 10 minutes</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-400" />
              <span>Cancel anytime</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Everything Your Shop Needs
          </h2>
          <p className="text-roadcall-muted text-lg max-w-2xl mx-auto">
            A complete AI phone system built specifically for mechanic shops,
            truck repair, and roadside service businesses.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <Card
              key={feature.title}
              className="bg-roadcall-panel/50 border-slate-700 hover:border-blue-500/50 transition-colors"
            >
              <CardHeader>
                <feature.icon className="h-10 w-10 text-blue-400 mb-2" />
                <CardTitle className="text-white">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-roadcall-muted text-base">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-roadcall-panel/30 py-20">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              How It Works
            </h2>
            <p className="text-roadcall-muted text-lg">
              Get set up in minutes, not days.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "1",
                title: "Tell Us About Your Shop",
                description:
                  "Enter your business name, services, hours, and pricing. We build your custom AI agent in seconds.",
              },
              {
                step: "2",
                title: "Get Your AI Phone Number",
                description:
                  "We assign a local or toll-free number, or forward your existing number to your AI receptionist.",
              },
              {
                step: "3",
                title: "Start Catching Every Lead",
                description:
                  "Your AI answers calls 24/7, captures leads, books appointments, and sends you real-time notifications.",
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-6">
                  {item.step}
                </div>
                <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
                <p className="text-roadcall-muted">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}

      {/* Pricing */}
      <section className="bg-roadcall-panel/30 py-20" id="pricing">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-roadcall-muted text-lg">
              No contracts. No hidden fees. Cancel anytime.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {plans.map((plan) => (
              <Card
                key={plan.name}
                className={`bg-roadcall-panel/50 border-slate-700 relative ${
                  plan.popular
                    ? "border-blue-500 ring-2 ring-blue-500/20"
                    : ""
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    MOST POPULAR
                  </div>
                )}
                <CardHeader className="text-center">
                  <CardTitle className="text-white text-xl">
                    {plan.name}
                  </CardTitle>
                  <CardDescription className="text-roadcall-muted">
                    {plan.description}
                  </CardDescription>
                  <div className="pt-4">
                    <span className="text-4xl font-bold text-white">
                      ${plan.price}
                    </span>
                    <span className="text-roadcall-muted">/month</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 mb-6">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2">
                        <CheckCircle2 className="h-5 w-5 text-green-400 shrink-0 mt-0.5" />
                        <span className="text-roadcall-silver/85 text-sm">{f}</span>
                      </li>
                    ))}
                  </ul>
                  <a href={plan.href} target="_blank" rel="noopener noreferrer">
                    <Button
                      className={`w-full ${
                        plan.popular
                          ? "bg-blue-600 hover:bg-blue-700"
                          : "bg-slate-700 hover:bg-slate-600"
                      }`}
                      size="lg"
                    >
                      Get Started
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </a>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="max-w-4xl mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl md:text-4xl font-bold mb-6">
          Ready to Stop Missing Calls?
        </h2>
        <p className="text-xl text-roadcall-silver/85 mb-8">
          Try the AI demo right now — call and hear it for yourself.
        </p>
        <a href={telHref(HELP_PHONE)}>
          <Button size="xl" className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-xl gap-3">
            <Phone className="h-6 w-6" />
            Call {HELP_PHONE} Now
          </Button>
        </a>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8">
        <div className="max-w-6xl mx-auto px-4 text-center text-roadcall-muted text-sm">
          <p>© {new Date().getFullYear()} AI Roadside Support. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
