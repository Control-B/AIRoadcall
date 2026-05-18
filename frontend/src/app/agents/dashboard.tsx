"use client";

import { useState } from "react";
import Link from "next/link";

export default function AgentDashboard() {
  const [agentType, setAgentType] = useState("mechanic");
  const [phone, setPhone] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleTestAgent = () => {
    // Placeholder for agent test logic (Retell integration)
    setTestResult("Test call initiated. (Simulated)");
  };

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Agent Dashboard</h1>
      <div className="mb-4">
        <label className="block font-medium mb-1">Agent Type</label>
        <select
          className="border rounded px-2 py-1 w-full"
          value={agentType}
          onChange={e => setAgentType(e.target.value)}
        >
          <option value="mechanic">Mechanic (Inbound only)</option>
          <option value="fleet">Fleet (Inbound & Outbound)</option>
        </select>
      </div>
      <div className="mb-4">
        <label className="block font-medium mb-1">Phone Number</label>
        <input
          className="border rounded px-2 py-1 w-full"
          type="tel"
          placeholder="Enter phone number"
          value={phone}
          onChange={e => setPhone(e.target.value)}
        />
      </div>
      {agentType === "fleet" && (
        <div className="mb-4">
          <label className="block font-medium mb-1">Outbound Call Options</label>
          <div className="text-sm text-gray-600">Fleet agents can make outbound calls.</div>
        </div>
      )}
      <button
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        onClick={handleTestAgent}
      >
        Test Agent
      </button>
      {testResult && <div className="mt-4 text-green-700">{testResult}</div>}
      <div className="mt-8 flex flex-col gap-2">
        <Link href="/get-started" className="text-blue-600 hover:underline">← Back to Get Started</Link>
        <Link href="/profile" className="text-blue-600 hover:underline">Go to Profile Setup</Link>
        <Link href="/retell" className="text-blue-600 hover:underline">Go to Retell Integration</Link>
      </div>
    </div>
  );
}
