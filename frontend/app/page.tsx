import Link from "next/link";
import { api, type CaseListItem } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  unsolved: "bg-red-950/60 text-red-300 border border-red-800/50",
  solved: "bg-emerald-950/60 text-emerald-300 border border-emerald-800/50",
  pending: "bg-amber-950/60 text-amber-300 border border-amber-800/50",
};

const DIFFICULTY_STYLES: Record<string, string> = {
  easy: "text-emerald-400",
  medium: "text-amber-400",
  hard: "text-red-400",
};

const DIFFICULTY_BARS: Record<string, number> = {
  easy: 1,
  medium: 2,
  hard: 3,
};

function DifficultyBar({ difficulty }: { difficulty: import("@/lib/api").CaseDifficulty | string }) {
  const diffStr = String(difficulty);
  const filled = DIFFICULTY_BARS[diffStr] ?? 2;
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          className={`inline-block h-2 w-4 rounded-sm ${
            i <= filled ? DIFFICULTY_STYLES[diffStr] ?? "text-zinc-500" : "bg-zinc-800"
          } ${i <= filled ? "bg-current opacity-80" : ""}`}
        />
      ))}
    </span>
  );
}

function CaseCard({ c }: { c: CaseListItem }) {
  return (
    <Link
      href={`/case/${c.id}/intro`}
      className="group relative flex flex-col rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6 transition-all duration-300 hover:border-zinc-600 hover:bg-zinc-900/80 hover:shadow-2xl hover:shadow-black/40"
    >
      {/* Status pill */}
      <div className="flex items-center justify-between gap-3">
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide uppercase ${
            STATUS_STYLES[c.status] ?? "bg-zinc-800 text-zinc-400"
          }`}
        >
          {c.status}
        </span>
        {c.year && (
          <span className="text-xs text-zinc-500 font-mono">{c.year}</span>
        )}
      </div>

      {/* Title */}
      <h2 className="mt-4 text-lg font-semibold tracking-tight text-zinc-100 group-hover:text-white">
        {c.title}
      </h2>

      {/* Subtitle */}
      <p className="mt-2 flex-1 text-sm text-zinc-400 leading-relaxed">{c.subtitle}</p>

      {/* Meta row */}
      <div className="mt-5 flex items-center justify-between gap-3 border-t border-zinc-800/60 pt-4">
        <div className="flex flex-col gap-1">
          {c.location && (
            <span className="text-xs text-zinc-500">
              <span className="mr-1">📍</span>{c.location}
            </span>
          )}
          {c.difficulty && (
            <div className="flex items-center gap-1.5">
              <DifficultyBar difficulty={c.difficulty} />
              <span className="text-xs text-zinc-500 capitalize">{String(c.difficulty)}</span>
            </div>
          )}
        </div>
        <span className="text-xs text-zinc-500 transition-colors group-hover:text-zinc-300">
          Open file →
        </span>
      </div>
    </Link>
  );
}

export default async function Home() {
  const cases = await api.listCases();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-sm">
        <div className="mx-auto max-w-5xl px-6 py-5 flex items-end justify-between gap-6">
          <div>
            <div className="text-xs font-mono text-zinc-500 tracking-widest uppercase mb-1">
              Case Archive
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
              IAM Detective
            </h1>
          </div>
          <p className="text-sm text-zinc-400 max-w-xs text-right hidden sm:block">
            Real cases. AI-powered investigation. Find the truth.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm text-zinc-500">
            {cases.length} case{cases.length !== 1 ? "s" : ""} in the archive
          </p>
        </div>

        <section className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {cases.map((c) => (
            <CaseCard key={c.id} c={c} />
          ))}
        </section>
      </main>
    </div>
  );
}
