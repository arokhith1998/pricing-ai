// Shown when the page cannot reach the Pricekeel API.
export default function ApiError() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <h1 className="text-2xl font-bold text-navy">Start the API</h1>
      <p className="mt-2 text-slate">
        This screen could not reach the Pricekeel API. Start it with:
      </p>
      <pre className="mt-3 rounded-lg bg-navy p-4 text-sm text-white">
        python -m uvicorn api.main:app --port 8000
      </pre>
    </main>
  );
}
