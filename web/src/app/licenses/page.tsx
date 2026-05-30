import type { Metadata } from "next";

export const metadata: Metadata = { title: "Open-Source Licenses · Pricekeel" };

// Manually curated to match requirements.txt + web/package.json runtime
// dependencies. Update when a major dep changes. The license string for
// each row reflects the license under which we receive the dependency
// (not necessarily its source repo's primary license, where they differ).

type Dep = { name: string; license: string; url: string; layer: string };

const DEPS: Dep[] = [
  // --- Web runtime ---
  { name: "next", license: "MIT", url: "https://github.com/vercel/next.js", layer: "web" },
  { name: "react", license: "MIT", url: "https://github.com/facebook/react", layer: "web" },
  { name: "react-dom", license: "MIT", url: "https://github.com/facebook/react", layer: "web" },
  { name: "framer-motion", license: "MIT", url: "https://github.com/framer/motion", layer: "web" },
  { name: "recharts", license: "MIT", url: "https://github.com/recharts/recharts", layer: "web" },
  { name: "@supabase/supabase-js", license: "MIT", url: "https://github.com/supabase/supabase-js", layer: "web" },
  { name: "marked", license: "MIT", url: "https://github.com/markedjs/marked", layer: "web" },
  { name: "tailwindcss", license: "MIT", url: "https://github.com/tailwindlabs/tailwindcss", layer: "web" },
  { name: "typescript", license: "Apache-2.0", url: "https://github.com/microsoft/TypeScript", layer: "web" },

  // --- API + analytics runtime (Python) ---
  { name: "fastapi", license: "MIT", url: "https://github.com/tiangolo/fastapi", layer: "api" },
  { name: "uvicorn", license: "BSD-3-Clause", url: "https://github.com/encode/uvicorn", layer: "api" },
  { name: "pydantic", license: "MIT", url: "https://github.com/pydantic/pydantic", layer: "api" },
  { name: "python-multipart", license: "Apache-2.0", url: "https://github.com/Kludex/python-multipart", layer: "api" },
  { name: "requests", license: "Apache-2.0", url: "https://github.com/psf/requests", layer: "api" },
  { name: "pandas", license: "BSD-3-Clause", url: "https://github.com/pandas-dev/pandas", layer: "analytics" },
  { name: "numpy", license: "BSD-3-Clause", url: "https://github.com/numpy/numpy", layer: "analytics" },
  { name: "scikit-learn", license: "BSD-3-Clause", url: "https://github.com/scikit-learn/scikit-learn", layer: "analytics" },
  { name: "lightgbm", license: "MIT", url: "https://github.com/microsoft/LightGBM", layer: "analytics" },
  { name: "rapidfuzz", license: "MIT", url: "https://github.com/maxbachmann/RapidFuzz", layer: "analytics" },
  { name: "fastembed", license: "Apache-2.0", url: "https://github.com/qdrant/fastembed", layer: "analytics" },
  { name: "openpyxl", license: "MIT", url: "https://foss.heptapod.net/openpyxl/openpyxl", layer: "ingest" },
  { name: "pypdf", license: "BSD-3-Clause", url: "https://github.com/py-pdf/pypdf", layer: "ingest" },
  { name: "python-docx", license: "MIT", url: "https://github.com/python-openxml/python-docx", layer: "ingest" },
  { name: "python-pptx", license: "MIT", url: "https://github.com/scanny/python-pptx", layer: "ingest" },
  { name: "openai", license: "Apache-2.0", url: "https://github.com/openai/openai-python", layer: "llm" },
  { name: "anthropic", license: "MIT", url: "https://github.com/anthropics/anthropic-sdk-python", layer: "llm" },
  { name: "tavily-python", license: "MIT", url: "https://github.com/tavily-ai/tavily-python", layer: "llm" },
];

const LAYERS: Record<string, string> = {
  web: "Web UI",
  api: "API layer",
  analytics: "Analytics + ML",
  ingest: "Document ingest",
  llm: "LLM clients",
};

export default function LicensesPage() {
  const layers = Array.from(new Set(DEPS.map((d) => d.layer)));
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Open-source licenses</h1>
      <p className="mt-2 text-sm text-muted">
        Pricekeel is built on permissively-licensed open-source software.
        Below is the list of runtime dependencies and the licenses under
        which we receive them.
      </p>

      {layers.map((layer) => (
        <section key={layer} className="mt-8">
          <h2 className="text-lg font-semibold text-fg">{LAYERS[layer] ?? layer}</h2>
          <div className="mt-2 overflow-x-auto rounded-xl border border-mist">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase tracking-wider text-muted">
                <tr>
                  <th className="px-3 py-2 font-semibold">Package</th>
                  <th className="px-3 py-2 font-semibold">License</th>
                  <th className="px-3 py-2 font-semibold">Source</th>
                </tr>
              </thead>
              <tbody>
                {DEPS.filter((d) => d.layer === layer).map((d) => (
                  <tr key={d.name} className="border-t border-mist align-top">
                    <td className="px-3 py-2 font-mono text-ink">{d.name}</td>
                    <td className="px-3 py-2 text-muted">{d.license}</td>
                    <td className="px-3 py-2">
                      <a className="text-teal underline" href={d.url} target="_blank" rel="noreferrer noopener">
                        repository
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      <p className="mt-10 text-sm leading-relaxed text-muted">
        All licenses above are permissive (MIT, Apache-2.0, BSD-3-Clause).
        Pricekeel does not depend on any copyleft (GPL / AGPL / LGPL)
        software in its runtime path. If you find an omission or error,
        please open an issue at{" "}
        <a className="text-teal underline" href="https://github.com/arokhith1998/pricing-ai" target="_blank" rel="noreferrer noopener">
          github.com/arokhith1998/pricing-ai
        </a>{" "}
        and we will fix it.
      </p>
    </main>
  );
}
