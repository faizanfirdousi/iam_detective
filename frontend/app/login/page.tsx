"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (res.ok) {
        router.push("/");
        router.refresh();
      } else {
        setError("Invalid credentials. Access denied.");
        setPassword("");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="h-[600px] w-[600px] rounded-full bg-red-950/20 blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo area */}
        <div className="mb-8 text-center">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-full border border-zinc-800 bg-zinc-900 text-2xl mb-4">
            🔍
          </div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100">IAM Detective</h1>
          <p className="mt-1 text-xs text-zinc-500 font-mono tracking-widest uppercase">
            Restricted Access
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-7 shadow-2xl backdrop-blur-sm">
          <p className="mb-5 text-sm text-zinc-400 text-center leading-relaxed">
            This application is restricted to authorized personnel only. Enter your credentials to proceed.
          </p>

          <form onSubmit={void handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                autoFocus
                autoComplete="username"
                required
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3.5 py-2.5 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-zinc-500 focus:ring-1 focus:ring-zinc-600 transition-colors"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                autoComplete="current-password"
                required
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3.5 py-2.5 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-zinc-500 focus:ring-1 focus:ring-zinc-600 transition-colors"
              />
            </div>

            {error && (
              <div className="rounded-lg border border-red-900/40 bg-red-950/40 px-3.5 py-2.5 text-xs text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="mt-1 w-full rounded-lg bg-zinc-100 py-2.5 text-sm font-semibold text-zinc-900 transition-colors hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? "Verifying…" : "Access Case Files →"}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-[11px] text-zinc-700">
          IAM Detective · Hackathon Demo · © 2026
        </p>
      </div>
    </div>
  );
}
