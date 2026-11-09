import type { Metadata } from "next";

export const metadata: Metadata = { title: "Open-Source Licenses · Pricekeel" };

// Regenerated 2026-11-09 from web/package.json "dependencies" (installed
// versions read from node_modules) and requirements.txt (installed versions
// read from the project venv). Direct runtime dependencies only, not
// transitive packages and not devDependencies. Update when a direct
// dependency is added, removed or relicensed. The license string is the
// one declared in the installed package metadata.

type Dep = { name: string; license: string; url: string; layer: string };

const DEPS: Dep[] = [
  // --- Web runtime (web/package.json dependencies) ---
  { name: "next", license: "MIT", url: "https://github.com/vercel/next.js", layer: "web" },
  { name: "react", license: "MIT", url: "https://github.com/facebook/react", layer: "web" },
  { name: "react-dom", license: "MIT", url: "https://github.com/facebook/react", layer: "web" },
  { name: "framer-motion", license: "MIT", url: "https://github.com/motiondivision/motion", layer: "web" },
  { name: "recharts", license: "MIT", url: "https://github.com/recharts/recharts", layer: "web" },
  { name: "@neondatabase/serverless", license: "MIT", url: "https://github.com/neondatabase/serverless", layer: "web" },
  { name: "@vercel/analytics", license: "MIT", url: "https://github.com/vercel/analytics", layer: "web" },
  { name: "marked", license: "MIT", url: "https://github.com/markedjs/marked", layer: "web" },
  { name: "sanitize-html", license: "MIT", url: "https://github.com/apostrophecms/sanitize-html", layer: "web" },

  // --- API runtime (Python, requirements.txt) ---
  { name: "fastapi", license: "MIT", url: "https://github.com/fastapi/fastapi", layer: "api" },
  { name: "uvicorn", license: "BSD-3-Clause", url: "https://github.com/encode/uvicorn", layer: "api" },
  { name: "python-multipart", license: "Apache-2.0", url: "https://github.com/Kludex/python-multipart", layer: "api" },
  { name: "psycopg", license: "LGPL-3.0-only", url: "https://github.com/psycopg/psycopg", layer: "api" },
  { name: "requests", license: "Apache-2.0", url: "https://github.com/psf/requests", layer: "api" },
  { name: "streamlit", license: "Apache-2.0", url: "https://github.com/streamlit/streamlit", layer: "api" },
  { name: "altair", license: "BSD-3-Clause", url: "https://github.com/vega/altair", layer: "api" },

  // --- Analytics + ML ---
  { name: "pandas", license: "BSD-3-Clause", url: "https://github.com/pandas-dev/pandas", layer: "analytics" },
  { name: "numpy", license: "BSD-3-Clause", url: "https://github.com/numpy/numpy", layer: "analytics" },
  { name: "scikit-learn", license: "BSD-3-Clause", url: "https://github.com/scikit-learn/scikit-learn", layer: "analytics" },
  { name: "lightgbm", license: "MIT", url: "https://github.com/lightgbm-org/LightGBM", layer: "analytics" },
  { name: "rapidfuzz", license: "MIT", url: "https://github.com/rapidfuzz/RapidFuzz", layer: "analytics" },
  { name: "fastembed", license: "Apache-2.0", url: "https://github.com/qdrant/fastembed", layer: "analytics" },

  // --- Document ingest ---
  { name: "openpyxl", license: "MIT", url: "https://foss.heptapod.net/openpyxl/openpyxl", layer: "ingest" },
  { name: "pypdf", license: "BSD-3-Clause", url: "https://github.com/py-pdf/pypdf", layer: "ingest" },
  { name: "python-docx", license: "MIT", url: "https://github.com/python-openxml/python-docx", layer: "ingest" },
  { name: "python-pptx", license: "MIT", url: "https://github.com/scanny/python-pptx", layer: "ingest" },

  // --- LLM and search clients ---
  { name: "anthropic", license: "MIT", url: "https://github.com/anthropics/anthropic-sdk-python", layer: "llm" },
  { name: "tavily-python", license: "MIT", url: "https://github.com/tavily-ai/tavily-python", layer: "llm" },
];

const LAYERS: Record<string, string> = {
  web: "Web UI",
  api: "API layer",
  analytics: "Analytics + ML",
  ingest: "Document ingest",
  llm: "LLM and search clients",
};

export default function LicensesPage() {
  const layers = Array.from(new Set(DEPS.map((d) => d.layer)));
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold text-fg">Open-source licenses</h1>
      <p className="mt-2 text-sm text-muted">
        Pricekeel is built on open-source software. Below is the list of
        direct runtime dependencies (not every transitive package) and the
        licenses under which we receive them. Last regenerated 9 November
        2026.
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
        Almost all licenses above are permissive (MIT, Apache-2.0,
        BSD-3-Clause). One exception: <code>psycopg</code>, our Postgres
        driver, is LGPL-3.0-only. We use it unmodified as an installed
        library. None of the direct dependencies listed here is GPL or
        AGPL. If you find an omission or error,
        please open an issue at{" "}
        <a className="text-teal underline" href="https://github.com/arokhith1998/pricing-ai" target="_blank" rel="noreferrer noopener">
          github.com/arokhith1998/pricing-ai
        </a>{" "}
        and we will fix it.
      </p>
    </main>
  );
}
