"use client";

import { useParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

export default function CasePage() {
  const params = useParams<{ id: string }>();
  const caseId = params.id;
  const router = useRouter();
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setErr(null);

    api
      .getMyCase(caseId)
      .then(async (p) => {
        if (!alive) return;
        if (!p.started_at) {
          await api.startCase(caseId);
          router.replace(`/case/${caseId}/intro`);
          return;
        }
        if (!p.intro_seen) {
          router.replace(`/case/${caseId}/intro`);
          return;
        }
        router.replace(`/case/${caseId}/workspace`);
      })
      .catch((e: unknown) => {
        if (alive) setErr(e instanceof Error ? e.message : String(e));
      });
    return () => {
      alive = false;
    };
  }, [caseId, router]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
          {err ? (
            <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-3 text-sm text-red-200">
              {err}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4 py-10">
              <div className="h-px w-16 animate-pulse bg-zinc-700" />
              <p className="text-xs font-mono tracking-[0.3em] text-zinc-600 uppercase">
                Opening case file…
              </p>
              <div className="h-px w-16 animate-pulse bg-zinc-700" />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
