"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api, type CaseDetail } from "@/lib/api";

export default function CasePage() {
  const params = useParams<{ id: string }>();
  const caseId = params.id;
  const [data, setData] = useState<CaseDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setErr(null);
    setData(null);
    api
      .getCase(caseId)
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((e: unknown) => {
        if (alive) setErr(e instanceof Error ? e.message : String(e));
      });
    return () => {
      alive = false;
    };
  }, [caseId]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <main className="mx-auto max-w-3xl px-6 py-10">
        <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-200">
          ← Back to cases
        </Link>

        <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-xl font-semibold tracking-tight">
              {data?.title ?? "Loading case…"}
            </h1>
            <span className="rounded-full border border-zinc-800 px-2 py-0.5 text-xs text-zinc-300">
              {data?.status ?? "—"}
            </span>
          </div>

          {err ? (
            <div className="mt-4 rounded-lg border border-red-900/60 bg-red-950/40 p-3 text-sm text-red-200">
              {err}
              <div className="mt-2 text-xs text-red-200/80">
                This should disappear once `DO_AGENT_ENDPOINT` + `DO_AGENT_ACCESS_KEY` are set for the backend.
              </div>
            </div>
          ) : (
            <div className="mt-4 space-y-2">
              {(data?.opening_lines ?? []).length === 0 ? (
                <p className="text-sm text-zinc-400">
                  Waiting for Gradient agent to generate opening lines…
                </p>
              ) : (
                data!.opening_lines.map((l, idx) => (
                  <p key={idx} className="text-sm text-zinc-200">
                    {l}
                  </p>
                ))
              )}
            </div>
          )}

          <div className="mt-6 flex items-center justify-between gap-3">
            <Link
              href={`/case/${caseId}/workspace`}
              className="rounded-lg bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-white"
            >
              Enter workspace
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

