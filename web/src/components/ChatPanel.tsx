"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Diagnostic } from "@/lib/api";

type Citation = {
  kind: "doc" | "analysis" | "web";
  title: string;
  snippet: string;
  detail: string;
};

type Message =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; citations: Citation[]; usedWeb: boolean };

type UploadedDoc = { name: string; chunks: number };

const SAMPLE_QUESTIONS = [
  "What does our policy say about discounts over 20%?",
  "Which deals look like packaging-fence problems, and why?",
  "What concessions should I ask for at 25% discount?",
];

function CitationChip({ c, n }: { c: Citation; n: number }) {
  const color =
    c.kind === "doc"
      ? "border-teal/40 text-teal"
      : c.kind === "web"
        ? "border-coral/40 text-coral"
        : "border-mist text-muted";
  return (
    <span
      title={`${c.title}${c.detail ? " · " + c.detail : ""}\n${c.snippet}`}
      className={`mx-0.5 inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold ${color}`}
    >
      {c.kind === "doc" ? `D${n}` : c.kind === "web" ? `W${n}` : "A"}
    </span>
  );
}

export default function ChatPanel({ analysis }: { analysis: Diagnostic }) {
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [docs, setDocs] = useState<UploadedDoc[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [useWeb, setUseWeb] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function uploadDocs(files: FileList | null) {
    if (!files || files.length === 0) return;
    setBusy(true);
    setError("");
    const fd = new FormData();
    for (const f of Array.from(files)) fd.append("files", f);
    if (sessionId) fd.append("session_id", sessionId);
    try {
      const r = await fetch("/api/docs", { method: "POST", body: fd });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(b.error || "Could not parse those documents.");
      }
      const data = await r.json();
      setSessionId(data.session_id);
      setDocs((prev) => [
        ...prev,
        ...(data.files as { name: string; chunks: number }[]).map((f) => ({
          name: f.name,
          chunks: f.chunks,
        })),
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Document parsing failed.");
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function ask(text: string) {
    const q = text.trim();
    if (!q) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setBusy(true);
    setError("");
    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q,
          session_id: sessionId,
          use_web: useWeb,
          analysis,
        }),
      });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(b.error || "Assistant failed.");
      }
      const data = await r.json();
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: data.text || "(no answer)",
          citations: data.citations || [],
          usedWeb: !!data.used_web,
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assistant failed.");
    } finally {
      setBusy(false);
    }
  }

  function renderAssistantText(m: Extract<Message, { role: "assistant" }>) {
    // Replace [D1], [W2], [A] tokens with citation chips.
    const docCites = m.citations.filter((c) => c.kind === "doc");
    const webCites = m.citations.filter((c) => c.kind === "web");
    const analysisCite = m.citations.find((c) => c.kind === "analysis");
    const parts: React.ReactNode[] = [];
    let i = 0;
    const re = /\[(D|W)(\d+)\]|\[A\]/g;
    let match: RegExpExecArray | null;
    while ((match = re.exec(m.text)) !== null) {
      if (match.index > i) parts.push(m.text.slice(i, match.index));
      if (match[0] === "[A]" && analysisCite) {
        parts.push(<CitationChip key={parts.length} c={analysisCite} n={0} />);
      } else if (match[1] === "D") {
        const n = parseInt(match[2] ?? "1", 10);
        const c = docCites[n - 1];
        if (c) parts.push(<CitationChip key={parts.length} c={c} n={n} />);
      } else if (match[1] === "W") {
        const n = parseInt(match[2] ?? "1", 10);
        const c = webCites[n - 1];
        if (c) parts.push(<CitationChip key={parts.length} c={c} n={n} />);
      }
      i = re.lastIndex;
    }
    if (i < m.text.length) parts.push(m.text.slice(i));
    return parts;
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-teal px-5 py-3 text-sm font-semibold text-bg shadow-lg shadow-teal/30 transition hover:scale-[1.03] hover:shadow-xl"
        aria-label="Open Ask the Analyst"
      >
        <span aria-hidden>✦</span> Ask the Analyst
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            key="overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 z-40 bg-bg/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
        ) : null}
        {open ? (
          <motion.aside
            key="panel"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 360, damping: 38 }}
            className="fixed bottom-0 right-0 top-0 z-50 flex w-full max-w-md flex-col border-l border-mist bg-surface shadow-2xl"
          >
            <header className="flex items-center justify-between border-b border-mist px-4 py-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-teal">
                  Ask the Analyst
                </div>
                <div className="text-sm text-muted">
                  Grounded in your analysis{docs.length ? ", uploaded docs" : ""}
                  {useWeb ? ", and the web" : ""}.
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="rounded p-1 text-muted hover:bg-mist hover:text-fg"
                aria-label="Close"
              >
                ✕
              </button>
            </header>

            {/* Docs row */}
            <div className="border-b border-mist px-4 py-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted">
                  {docs.length === 0
                    ? "Add policy / playbook / contracts for richer answers."
                    : `${docs.length} doc${docs.length === 1 ? "" : "s"}, ${docs.reduce((s, d) => s + d.chunks, 0)} chunks indexed.`}
                </span>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={busy}
                  className="rounded-lg border border-mist bg-surface-2 px-2 py-1 text-xs font-medium text-fg hover:border-teal"
                >
                  + add
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.md,.txt"
                  onChange={(e) => uploadDocs(e.target.files)}
                  className="hidden"
                />
              </div>
              {docs.length > 0 ? (
                <ul className="mt-2 space-y-1 text-xs text-muted">
                  {docs.map((d, i) => (
                    <li key={i} className="truncate">
                      <span className="text-teal">●</span> {d.name}{" "}
                      <span className="text-mist">— {d.chunks} chunks</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>

            {/* Conversation */}
            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {messages.length === 0 ? (
                <div className="space-y-2">
                  <p className="text-sm text-muted">
                    Ask anything about your analysis or the documents you have
                    uploaded. Every claim cites a source: [A] analysis, [D#]
                    document chunks, [W#] web.
                  </p>
                  <div className="space-y-1.5">
                    {SAMPLE_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        onClick={() => ask(q)}
                        disabled={busy}
                        className="block w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-left text-xs text-fg hover:border-teal"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-navy px-3 py-2 text-sm text-white">
                      {m.text}
                    </div>
                  </div>
                ) : (
                  <div key={i} className="flex flex-col gap-1">
                    <div className="max-w-[95%] rounded-2xl rounded-bl-sm border border-mist bg-surface-2 px-3 py-2 text-sm leading-relaxed text-ink">
                      {renderAssistantText(m)}
                    </div>
                    {m.usedWeb ? (
                      <span className="text-[10px] text-muted">web search was used</span>
                    ) : null}
                  </div>
                ),
              )}

              {busy ? (
                <div className="text-xs text-muted">Thinking…</div>
              ) : null}
              {error ? <div className="text-xs text-coral">{error}</div> : null}
            </div>

            {/* Composer */}
            <footer className="border-t border-mist px-4 py-3">
              <div className="mb-2 flex items-center gap-3 text-xs">
                <label className="flex items-center gap-1.5 text-muted">
                  <input
                    type="checkbox"
                    checked={useWeb}
                    onChange={(e) => setUseWeb(e.target.checked)}
                    className="h-3.5 w-3.5 accent-teal"
                  />
                  Search the web
                </label>
                <span className="ml-auto text-[10px] text-muted">
                  Row data never leaves the server.
                </span>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  ask(input);
                }}
                className="flex items-end gap-2"
              >
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      ask(input);
                    }
                  }}
                  placeholder="Ask about the analysis or the docs you uploaded…"
                  rows={2}
                  className="flex-1 resize-none rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-fg focus:border-teal focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={busy || !input.trim()}
                  className="rounded-lg bg-teal px-3 py-2 text-sm font-semibold text-bg transition hover:scale-[1.03] disabled:opacity-50"
                >
                  Ask
                </button>
              </form>
            </footer>
          </motion.aside>
        ) : null}
      </AnimatePresence>
    </>
  );
}
