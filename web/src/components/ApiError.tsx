// Shown when the page cannot reach the Pricekeel analysis engine.
// Buyer-facing copy only: no commands, no developer jargon.
export default function ApiError() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <h1 className="text-2xl font-bold text-fg">
        The live sample is briefly unavailable
      </h1>
      <p className="mt-2 max-w-xl text-slate">
        The analysis engine is restarting. It usually takes under a minute.
        Refresh to retry, or email{" "}
        <a
          className="text-teal underline"
          href="mailto:adhithya@pricekeel.com?subject=Pricekeel%20sample%20read-out"
        >
          adhithya@pricekeel.com
        </a>{" "}
        and I will send you the read-out directly.
      </p>
    </main>
  );
}
