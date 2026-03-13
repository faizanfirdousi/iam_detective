"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { api, type CaseIntroSlide } from "@/lib/api";

// Background colour palettes for each slide (dark atmospheric)
const SLIDE_PALETTES = [
  { bg: "from-zinc-950 via-slate-900 to-zinc-950", accent: "#a78bfa" }, // deep purple
  { bg: "from-zinc-950 via-red-950/30 to-zinc-950", accent: "#fca5a5" }, // dark red
  { bg: "from-zinc-950 via-blue-950/30 to-zinc-950", accent: "#93c5fd" }, // cold blue
  { bg: "from-zinc-950 via-amber-950/20 to-zinc-950", accent: "#fcd34d" }, // amber
];

function useTypewriter(text: string, speed = 28) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);
    if (!text) return;
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayed, done };
}

function SlideView({
  slide,
  palette,
  onNext,
  isLast,
  caseId,
}: {
  slide: CaseIntroSlide;
  palette: (typeof SLIDE_PALETTES)[0];
  onNext: () => void;
  isLast: boolean;
  caseId: string;
}) {
  const { displayed, done } = useTypewriter(slide.text);

  return (
    <div
      className={`absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-b ${palette.bg} px-6 animate-fadeIn`}
    >
      {/* Slide number */}
      <div className="absolute top-8 left-0 right-0 flex justify-center">
        <span className="font-mono text-xs tracking-[0.3em] text-zinc-600 uppercase">
          {String(slide.page).padStart(2, "0")} / 04
        </span>
      </div>

      {/* Decorative horizontal line */}
      <div
        className="mb-10 h-px w-16 opacity-40"
        style={{ backgroundColor: palette.accent }}
      />

      {/* Text */}
      <p className="max-w-2xl text-center text-xl font-light leading-relaxed tracking-wide text-zinc-200 md:text-2xl">
        {displayed}
        {!done && (
          <span
            className="ml-0.5 inline-block w-0.5 h-5 animate-blink align-middle"
            style={{ backgroundColor: palette.accent }}
          />
        )}
      </p>

      {/* CTA — show after typewriter finishes */}
      <div
        className={`absolute bottom-14 transition-all duration-700 ${
          done ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
        }`}
      >
        {isLast ? (
          <Link
            href={`/case/${caseId}/workspace`}
            className="group flex items-center gap-3 rounded-full border border-zinc-700 bg-zinc-900/80 px-8 py-3.5 text-sm font-medium text-zinc-200 backdrop-blur-sm transition-all hover:border-zinc-400 hover:text-white"
          >
            <span>Begin Investigation</span>
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
        ) : (
          <button
            onClick={onNext}
            className="group flex items-center gap-3 rounded-full border border-zinc-800 bg-zinc-900/60 px-7 py-3 text-sm text-zinc-400 backdrop-blur-sm transition-all hover:border-zinc-600 hover:text-zinc-200"
          >
            <span>Continue</span>
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </button>
        )}
      </div>

      {/* Skip link */}
      <Link
        href={`/case/${caseId}/workspace`}
        className="absolute bottom-5 right-6 text-xs text-zinc-700 transition-colors hover:text-zinc-500"
      >
        Skip intro
      </Link>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950">
      <div className="flex flex-col items-center gap-4">
        <div className="h-px w-16 animate-pulse bg-zinc-700" />
        <p className="text-xs font-mono tracking-[0.3em] text-zinc-600 uppercase">
          Accessing case file…
        </p>
        <div className="h-px w-16 animate-pulse bg-zinc-700" />
      </div>
    </div>
  );
}

function ErrorScreen({ err, caseId }: { err: string; caseId: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-950 px-6">
      <p className="max-w-md text-center text-sm text-red-300/80">
        Could not load case file. The agent may not be configured.
      </p>
      <code className="rounded-lg bg-red-950/40 px-4 py-2 text-xs text-red-400 border border-red-900/40">
        {err}
      </code>
      <div className="flex gap-4">
        <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-300">
          ← Back to archive
        </Link>
        <Link
          href={`/case/${caseId}/workspace`}
          className="text-sm text-zinc-400 hover:text-zinc-200"
        >
          Skip to workspace →
        </Link>
      </div>
    </div>
  );
}

export default function IntroPage() {
  const params = useParams<{ id: string }>();
  const caseId = params.id;

  const [slides, setSlides] = useState<CaseIntroSlide[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [transitioning, setTransitioning] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .getIntroSlides(caseId)
      .then((s) => {
        if (alive) {
          // Sort by page number to be safe
          setSlides(s.sort((a, b) => a.page - b.page));
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (alive) {
          setErr(e instanceof Error ? e.message : String(e));
          setLoading(false);
        }
      });
    return () => { alive = false; };
  }, [caseId]);

  const goNext = useCallback(() => {
    if (transitioning) return;
    setTransitioning(true);
    setTimeout(() => {
      setCurrentSlide((s) => s + 1);
      setTransitioning(false);
    }, 400);
  }, [transitioning]);

  if (loading) return <LoadingScreen />;
  if (err || slides.length === 0)
    return <ErrorScreen err={err ?? "no_slides"} caseId={caseId} />;

  const slide = slides[currentSlide] ?? slides[slides.length - 1];
  const palette = SLIDE_PALETTES[currentSlide % SLIDE_PALETTES.length];
  const isLast = currentSlide >= slides.length - 1;

  return (
    <div
      className={`relative min-h-screen overflow-hidden transition-opacity duration-400 ${
        transitioning ? "opacity-0" : "opacity-100"
      }`}
    >
      <SlideView
        key={currentSlide}
        slide={slide}
        palette={palette}
        onNext={goNext}
        isLast={isLast}
        caseId={caseId}
      />

      {/* Back link top-left */}
      <Link
        href="/"
        className="absolute top-6 left-6 text-xs text-zinc-700 transition-colors hover:text-zinc-500"
      >
        ← Archive
      </Link>
    </div>
  );
}
