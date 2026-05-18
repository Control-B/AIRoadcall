export default function AgentsIndexPage() {
  return (
    <div className="max-w-xl mx-auto p-8 text-center">
      <h1 className="text-3xl font-bold mb-4">Agents</h1>
      <p className="mb-6">Select an agent dashboard:</p>
      <a href="/agents/dashboard" className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition">Agent Dashboard</a>
    </div>
  );
}
