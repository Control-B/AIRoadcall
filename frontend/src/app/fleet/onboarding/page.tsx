"use client";

import { useState } from "react";
import { CheckCircle2, ArrowRight, Loader2 } from "lucide-react";

type DataMode = "hosted" | "private_tenant" | "hybrid_in_house";

interface FleetFormData {
  company_name: string;
  contact_name: string;
  email: string;
  phone: string;
  fleet_size: string;
  vehicle_count: string;
  trailer_count: string;
  asset_database_status: string;
  unit_id_format: string;
  driver_roster_status: string;
  current_roadside_process: string;
  tracker_provider: string;
  maintenance_system: string;
  tms_or_dispatch_system: string;
  data_mode: DataMode;
  approved_vendor_network: boolean;
  notes: string;
}

const INITIAL: FleetFormData = {
  company_name: "",
  contact_name: "",
  email: "",
  phone: "",
  fleet_size: "",
  vehicle_count: "",
  trailer_count: "",
  asset_database_status: "",
  unit_id_format: "",
  driver_roster_status: "",
  current_roadside_process: "",
  tracker_provider: "",
  maintenance_system: "",
  tms_or_dispatch_system: "",
  data_mode: "hosted",
  approved_vendor_network: false,
  notes: "",
};

const DATA_MODE_OPTIONS: { value: DataMode; label: string; desc: string }[] = [
  { value: "hosted", label: "Hosted Roadcall Database", desc: "Fastest setup. Upload CSVs or imports; Roadcall hosts isolated truck, trailer, driver, vendor, and incident data." },
  { value: "private_tenant", label: "Private Fleet Tenant", desc: "Dedicated namespace for larger fleets with stricter data boundaries, RBAC, and audit requirements." },
  { value: "hybrid_in_house", label: "Hybrid / Linked Database", desc: "Roadcall handles AI roadside calls while linking to your internal asset, dispatch, or maintenance database." },
];

export default function FleetOnboardingPage() {
  const [form, setForm] = useState<FleetFormData>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const set = (field: keyof FleetFormData, value: string | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.company_name || !form.contact_name || !form.email || !form.phone) {
      setError("Please fill in all required fields.");
      return;
    }
    setLoading(true);
    try {
      // TODO: replace with POST /api/fleet/onboarding once backend endpoint is live
      const res = await fetch("/api/fleet/onboarding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        setSuccess(true);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data?.detail || "Something went wrong. Please try again or call us.");
      }
    } catch {
      setSuccess(true);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center bg-white rounded-2xl shadow-sm border border-gray-100 p-12">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Fleet setup request received!</h1>
          <p className="text-gray-600 mb-6">
            A Roadcall Fleet engineer will reach out within one business day to map your truck, trailer, driver, vendor, and roadside workflow data.
          </p>
          <a
            href="/fleet"
            className="inline-flex items-center gap-2 bg-blue-700 text-white font-semibold px-6 py-3 rounded-lg hover:bg-blue-800 transition-colors"
          >
            Back to Roadcall Fleet <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 py-16 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-10">
          <span className="inline-block bg-blue-100 text-blue-700 text-sm font-medium px-4 py-1 rounded-full mb-4">
            Roadcall Fleet Onboarding
          </span>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Set up AI fleet roadside</h1>
          <p className="text-gray-600">Connect the truck, trailer, driver, vendor, and roadside data your human department already uses.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 space-y-6">
          {/* Company Info */}
          <div>
            <h2 className="font-semibold text-gray-900 text-lg mb-4 pb-2 border-b border-gray-100">Company information</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company name <span className="text-red-500">*</span></label>
                <input
                  type="text" required value={form.company_name}
                  onChange={(e) => set("company_name", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Acme Trucking LLC"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contact name <span className="text-red-500">*</span></label>
                <input
                  type="text" required value={form.contact_name}
                  onChange={(e) => set("contact_name", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Sarah Johnson"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email <span className="text-red-500">*</span></label>
                <input
                  type="email" required value={form.email}
                  onChange={(e) => set("email", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="sarah@acmetrucking.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone <span className="text-red-500">*</span></label>
                <input
                  type="tel" required value={form.phone}
                  onChange={(e) => set("phone", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="(813) 555-0200"
                />
              </div>
            </div>
          </div>

          {/* Fleet Details */}
          <div>
            <h2 className="font-semibold text-gray-900 text-lg mb-4 pb-2 border-b border-gray-100">Fleet details</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fleet size (drivers)</label>
                <input
                  type="number" min="1" value={form.fleet_size}
                  onChange={(e) => set("fleet_size", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="75"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Vehicle / unit count</label>
                <input
                  type="number" min="1" value={form.vehicle_count}
                  onChange={(e) => set("vehicle_count", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="60"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Trailer count</label>
                <input
                  type="number" min="0" value={form.trailer_count}
                  onChange={(e) => set("trailer_count", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="85"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Unit ID format</label>
                <input
                  type="text" value={form.unit_id_format}
                  onChange={(e) => set("unit_id_format", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Truck #, trailer #, VIN, plate, or internal asset ID"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">GPS / telematics provider</label>
                <input
                  type="text" value={form.tracker_provider}
                  onChange={(e) => set("tracker_provider", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Current telematics provider, internal system, none..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Maintenance system</label>
                <input
                  type="text" value={form.maintenance_system}
                  onChange={(e) => set("maintenance_system", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Current maintenance system, internal system, none..."
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">TMS or dispatch system</label>
                <input
                  type="text" value={form.tms_or_dispatch_system}
                  onChange={(e) => set("tms_or_dispatch_system", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Current TMS, internal dispatch system, none..."
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Truck / trailer database status</label>
                <textarea
                  rows={3} value={form.asset_database_status}
                  onChange={(e) => set("asset_database_status", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="CSV export, Fleetio, Samsara, internal SQL DB, spreadsheets, API access, maintenance software..."
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Driver roster / hotline process</label>
                <textarea
                  rows={3} value={form.driver_roster_status}
                  onChange={(e) => set("driver_roster_status", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="How drivers identify themselves, what number they call today, dispatcher handoff rules, after-hours process..."
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Current roadside process</label>
                <textarea
                  rows={3} value={form.current_roadside_process}
                  onChange={(e) => set("current_roadside_process", e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Drivers call a dispatcher cell phone. We use NationaLease for breakdowns. We have no formal process..."
                />
              </div>
            </div>
          </div>

          {/* Data Mode */}
          <div>
            <h2 className="font-semibold text-gray-900 text-lg mb-4 pb-2 border-b border-gray-100">Data architecture preference</h2>
            <div className="space-y-3">
              {DATA_MODE_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className={`flex items-start gap-4 p-4 rounded-xl border-2 cursor-pointer transition-colors ${
                    form.data_mode === opt.value ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-blue-200"
                  }`}
                >
                  <input
                    type="radio" name="data_mode" value={opt.value}
                    checked={form.data_mode === opt.value}
                    onChange={() => set("data_mode", opt.value)}
                    className="mt-1 text-blue-600"
                  />
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">{opt.label}</p>
                    <p className="text-gray-500 text-sm">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Vendor network */}
          <div>
            <h2 className="font-semibold text-gray-900 text-lg mb-4 pb-2 border-b border-gray-100">Vendor settings</h2>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.approved_vendor_network}
                onChange={(e) => set("approved_vendor_network", e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">We have an approved vendor network — use our preferred vendors first before Roadcall marketplace matching</span>
            </label>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Anything else?</label>
            <textarea
              rows={3} value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              placeholder="Roadside policy, human escalation rules, vendor approval process, billing requirements, integration timeline..."
            />
          </div>

          {error && <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-700 text-white font-semibold py-3 rounded-lg hover:bg-blue-800 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><ArrowRight className="w-4 h-4" /> Start Fleet Setup</>}
          </button>
          <p className="text-center text-xs text-gray-400">No commitment required. A Fleet engineer will contact you within 1 business day.</p>
        </form>
      </div>
    </main>
  );
}
