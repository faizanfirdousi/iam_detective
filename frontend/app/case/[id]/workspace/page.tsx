"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  api,
  type LinkNode,
  type SessionBoard,
  type SessionChatResponse,
  type StageInfo,
  type TimelineEvent,
} from "@/lib/api";
import Pinboard, { NODE_COLORS, type PinboardHandle } from "@/components/Pinboard";
import TimelineView from "@/components/TimelineView";

// ── Toast type ───────────────────────────────────────────────────────────────
type Toast = { id: number; text: string; type: "evidence" | "contradiction" | "stage" };

// ── Chat message ─────────────────────────────────────────────────────────────
type ChatMsg = { from: "you" | "agent"; text: string };

const NOTES_KEY = (caseId: string) => `iam_notes_${caseId}`;

// ── Legacy node style helper (used by evidence drawer) ───────────────────────
const NODE_STYLES: Record<string, { label: string }> = {
  suspect:  { label: "text-red-400" },
  victim:   { label: "text-zinc-400" },
  witness:  { label: "text-blue-400" },
  evidence: { label: "text-amber-400" },
  location: { label: "text-emerald-400" },
  event:    { label: "text-purple-400" },
};
const gs = (t: string) => NODE_STYLES[t.toLowerCase()] ?? NODE_STYLES.evidence;

// ── Stage metadata ────────────────────────────────────────────────────────────
const STAGE_META = [
  { name: "Crime Scene",     icon: "🔦" },
  { name: "Forensics",       icon: "🧪" },
  { name: "Witnesses",       icon: "👁" },
  { name: "Suspects",        icon: "🎯" },
  { name: "Case Building",   icon: "🗂" },
  { name: "The Verdict",     icon: "⚖️" },
];

// ── Stage Progress Bar ────────────────────────────────────────────────────────
function StageProgressBar({
  currentStage,
  completedStages,
  canAdvance,
  onAdvance,
  advancing,
}: {
  currentStage: number;
  completedStages: number[];
  canAdvance: boolean;
  onAdvance: () => void;
  advancing: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5 px-4 py-2 border-b border-zinc-800/60 bg-zinc-950/95 backdrop-blur-sm overflow-x-auto">
      <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mr-1 shrink-0">CASE FILE</span>
      {STAGE_META.map((meta, i) => {
        const stageNum = i + 1;
        const isDone = completedStages.includes(stageNum);
        const isCurrent = currentStage === stageNum;
        const isLocked = !isDone && !isCurrent;
        return (
          <div key={i} className="flex items-center gap-1 shrink-0">
            <div
              className={[
                "text-[10px] font-mono px-2 py-1 rounded border transition-all duration-300 select-none whitespace-nowrap",
                isDone
                  ? "border-emerald-700/60 text-emerald-400 bg-emerald-950/40"
                  : isCurrent
                  ? "border-red-600/70 text-red-300 bg-red-950/50 ring-1 ring-red-700/30 animate-pulse"
                  : "border-zinc-800 text-zinc-600 bg-transparent",
              ].join(" ")}
            >
              {isDone ? "✓" : meta.icon} {stageNum}. {meta.name}
            </div>
            {i < 5 && (
              <div
                className={[
                  "w-4 h-px shrink-0 transition-all duration-500",
                  isDone ? "bg-emerald-700/60" : "bg-zinc-800",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}

      {/* Advance button */}
      {canAdvance && currentStage < 6 && (
        <button
          onClick={onAdvance}
          disabled={advancing}
          className={[
            "ml-3 shrink-0 text-[10px] font-mono px-3 py-1.5 rounded border transition-all duration-200",
            advancing
              ? "border-zinc-700 text-zinc-600 cursor-wait"
              : "border-red-700/70 bg-red-950/60 text-red-300 hover:bg-red-900/60 hover:border-red-600 hover:text-red-200 shadow-sm shadow-red-950",
          ].join(" ")}
        >
          {advancing ? "UNLOCKING…" : "ADVANCE STAGE →"}
        </button>
      )}
      {currentStage === 6 && (
        <span className="ml-3 shrink-0 text-[10px] font-mono text-amber-500/80 border border-amber-700/40 bg-amber-950/20 px-2 py-1 rounded">
          ⚖️ VERDICT STAGE
        </span>
      )}
    </div>
  );
}

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const caseId = params.id;

  // Session
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [board, setBoard] = useState<SessionBoard | null>(null);
  const [boardLoading, setBoardLoading] = useState(true);
  const [boardErr, setBoardErr] = useState<string | null>(null);

  // Pinboard ref for programmatic refresh
  const pinboardRef = useRef<PinboardHandle>(null);

  // Selected pinboard node (for slide-in detail panel)
  const [selectedPinNode, setSelectedPinNode] = useState<Record<string, unknown> | null>(null);

  // Tabs
  const [activeTab, setActiveTab] = useState<"pinboard" | "timeline">("pinboard");
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

  // Chat
  const [role, setRole] = useState<string>("co_detective");
  const [personaId, setPersonaId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [chatHistories, setChatHistories] = useState<Record<string, ChatMsg[]>>({});
  const [sending, setSending] = useState(false);

  const currentChatKey = personaId ? `${role}:${personaId}` : role;
  const currentChat = chatHistories[currentChatKey] || [];

  // Evidence drawer (board-level node, kept for evidence present logic)
  const [selectedNode, setSelectedNode] = useState<LinkNode | null>(null);

  // Toasts
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastIdRef = useRef(0);

  // Notes
  const [notesOpen, setNotesOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [notesSaved, setNotesSaved] = useState(true);

  // Conclusion
  const [concludeOpen, setConcludeOpen] = useState(false);
  const [conclusion, setConclusion] = useState({ killer: "", motive: "", method: "" });
  const [concludeResult, setConcludeResult] = useState<null | { score: number; max_score: number; percentage: number; feedback: string; official_verdict: string }>(null);

  // Stage
  const [stageInfo, setStageInfo] = useState<StageInfo | null>(null);
  const [advancingStage, setAdvancingStage] = useState(false);

  const addToast = useCallback((text: string, type: Toast["type"]) => {
    const id = ++toastIdRef.current;
    setToasts(t => [...t, { id, text, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), type === "stage" ? 8000 : 5000);
  }, []);

  // Load notes
  useEffect(() => {
    if (!sessionId) return;
    api.getNotes(sessionId).then(res => {
      if (res.notes) setNotes(res.notes);
    }).catch(() => { /* ignore */ });
  }, [sessionId]);

  // Auto-save notes
  useEffect(() => {
    if (!sessionId) return;
    setNotesSaved(false);
    const t = setTimeout(() => {
      api.saveNotes(sessionId, notes).then(() => {
        setNotesSaved(true);
      }).catch(() => { /* ignore */ });
    }, 1000);
    return () => clearTimeout(t);
  }, [notes, sessionId]);

  // Fetch stage info helper
  const fetchStageInfo = useCallback(async (sid: string) => {
    try {
      const info = await api.getStage(sid);
      setStageInfo(info);
    } catch { /* ignore */ }
  }, []);

  // Fetch timeline helper
  const fetchTimeline = useCallback(async (sid: string) => {
    try {
      const res = await api.getTimeline(sid);
      setTimelineEvents(res.events);
    } catch { /* ignore */ }
  }, []);

  // Create session + load board
  useEffect(() => {
    let alive = true;
    setBoardLoading(true);
    setBoardErr(null);

    api
      .createSession(caseId)
      .then((session) => {
        if (!alive) return;
        setSessionId(session.session_id);
        // Fetch board + stage info in parallel
        return Promise.all([
          api.getSessionBoard(session.session_id),
          api.getStage(session.session_id),
          api.getTimeline(session.session_id),
        ]).then(([b, si, tl]) => {
          if (!alive) return;
          setBoard(b);
          setStageInfo(si);
          setTimelineEvents(tl.events);
          setBoardLoading(false);
          // Welcome message from the AI's first stage
          setChatHistories({
            co_detective: [{
              from: "agent",
              text: `🔦 Stage 1: ${si.stage_description}\n\nA new case file has been opened. Start by examining the crime scene. What do you see?`,
            }]
          });
        });
      })
      .catch((e: unknown) => {
        if (!alive) return;
        setBoardErr(e instanceof Error ? e.message : String(e));
        setBoardLoading(false);
      });

    return () => { alive = false; };
  }, [caseId, fetchStageInfo, fetchTimeline]);

  // Refresh board helper
  const refreshBoard = useCallback(async () => {
    if (!sessionId) return;
    try {
      const [b, si, tl] = await Promise.all([
        api.getSessionBoard(sessionId),
        api.getStage(sessionId),
        api.getTimeline(sessionId),
      ]);
      setBoard(b);
      setStageInfo(si);
      setTimelineEvents(tl.events);
    } catch { /* ignore */ }
  }, [sessionId]);

  // Handle stage advance
  const handleAdvanceStage = useCallback(async () => {
    if (!sessionId || advancingStage) return;
    setAdvancingStage(true);
    try {
      const result = await api.advanceStage(sessionId);
      await refreshBoard();
      await pinboardRef.current?.refresh();

      const newCount = result.newly_unlocked_entities.length;
      addToast(
        `🔓 Stage ${result.new_stage} unlocked: ${result.stage_name}${newCount > 0 ? ` — ${newCount} new connection${newCount !== 1 ? "s" : ""} revealed` : ""}`,
        "stage"
      );

      // Inject a co-detective message for the new stage
      setChatHistories(prev => ({
        ...prev,
        co_detective: [
          ...(prev.co_detective || []),
          {
            from: "agent",
            text: `🏁 STAGE COMPLETED.\n\nGood work on the ${STAGE_META[currentStage - 1].name}. We've gathered some crucial info. Now, let's move into ${result.stage_name.toUpperCase()}.\n\nMISSION: ${result.stage_description}\n\n${
              newCount > 0
                ? `New evidence has emerged: ${result.newly_unlocked_entities.map(e => e.name).join(", ")}. Study it carefully.`
                : "A new phase of the investigation begins. What's your next move?"
            }`,
          }
        ]
      }));
    } catch (e: unknown) {
      addToast(`⚠️ Could not advance stage: ${e instanceof Error ? e.message : String(e)}`, "evidence");
    } finally {
      setAdvancingStage(false);
    }
  }, [sessionId, advancingStage, refreshBoard, addToast]);

  // Chat send — uses session API
  async function send() {
    const msg = input.trim();
    if (!msg || sending || !sessionId) return;
    
    const key = currentChatKey;
    setInput("");
    setChatHistories(prev => ({
      ...prev,
      [key]: [...(prev[key] || []), { from: "you", text: msg }]
    }));
    
    setSending(true);
    try {
      const res: SessionChatResponse = await api.sessionChat(sessionId, {
        message: msg,
        role,
        persona_id: personaId,
      });
      
      setChatHistories(prev => ({
        ...prev,
        [key]: [...(prev[key] || []), { from: "agent", text: res.reply }]
      }));

      // Toasts for newly unlocked
      for (const u of res.newly_unlocked) {
        addToast(`📋 New ${u.type}: ${u.name}`, "evidence");
      }
      // Toasts for contradictions
      for (const ct of res.contradictions) {
        addToast(`⚡ Contradiction detected: ${ct.claim}`, "contradiction");
      }

      // Refresh board + pinboard if anything was unlocked
      if (res.newly_unlocked.length > 0 || res.contradictions.length > 0) {
        await refreshBoard();
        await pinboardRef.current?.refresh();
      } else {
        // Still update stage state to check if advance became available
        if (sessionId) void fetchStageInfo(sessionId);
      }
    } catch (e: unknown) {
      setChatHistories(prev => ({
        ...prev,
        [key]: [...(prev[key] || []), { from: "agent", text: e instanceof Error ? e.message : String(e) }]
      }));
    } finally {
      setSending(false);
    }
  }

  // Present evidence
  async function presentEvidence(evidenceId: string, suspectId: string) {
    if (!sessionId) return;
    const key = `suspect:${suspectId}`;
    setSending(true);
    try {
      const res = await api.presentEvidence(sessionId, evidenceId, suspectId);
      setChatHistories(prev => ({
        ...prev,
        [key]: [
          ...(prev[key] || []),
          { from: "you", text: `[Presented evidence: ${evidenceId}]` },
          { from: "agent", text: res.reply }
        ]
      }));
      for (const ct of res.contradictions) {
        addToast(`⚡ ${ct.claim}`, "contradiction");
      }
      await refreshBoard();
    } catch (e: unknown) {
      setChatHistories(prev => ({
        ...prev,
        [key]: [...(prev[key] || []), { from: "agent", text: e instanceof Error ? e.message : String(e) }]
      }));
    } finally {
      setSending(false);
    }
  }

  // Submit conclusion
  async function submitConclusion() {
    if (!sessionId) return;
    try {
      const res = await api.conclude(sessionId, conclusion);
      setConcludeResult(res);
    } catch (e: unknown) {
      setConcludeResult({ score: 0, max_score: 100, percentage: 0, feedback: e instanceof Error ? e.message : String(e), official_verdict: "Error" });
    }
  }

  // Extract suspects and evidence for dropdowns
  const suspectNodes = board?.nodes.filter(n => n.type.toLowerCase() === "suspect") ?? [];
  const evidenceNodes = board?.nodes.filter(n => n.type.toLowerCase() === "evidence") ?? [];

  // Stage info from board (fallback to stageInfo state)
  const currentStage = stageInfo?.current_stage ?? board?.stage ?? 1;
  const completedStages = stageInfo?.completed_stages ?? [];
  const canAdvance = stageInfo?.can_advance ?? board?.can_advance ?? false;

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center justify-between gap-4 border-b border-zinc-800 bg-zinc-950/90 px-5 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">← Archive</Link>
          <div className="h-4 w-px bg-zinc-800" />
          <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider">{caseId.replace(/-/g, " ")}</span>
          {sessionId && (
            <>
              <div className="h-4 w-px bg-zinc-800" />
              <span className="text-[10px] font-mono text-zinc-600">SID: {sessionId}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setNotesOpen(!notesOpen)} className={`rounded-lg px-3 py-1.5 text-xs transition-colors ${notesOpen ? "bg-zinc-700 text-zinc-200" : "text-zinc-500 hover:text-zinc-300"}`}>📝 Notes</button>
          <button onClick={() => setConcludeOpen(true)} className="rounded-lg px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors">🏁 Conclude</button>
        </div>
      </header>

      {/* Stage progress bar */}
      <StageProgressBar
        currentStage={currentStage}
        completedStages={completedStages}
        canAdvance={canAdvance}
        onAdvance={() => void handleAdvanceStage()}
        advancing={advancingStage}
      />

      {/* Toasts */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map(t => (
          <div
            key={t.id}
            className={[
              "animate-fadeIn rounded-lg px-4 py-3 text-sm shadow-xl backdrop-blur-sm max-w-sm",
              t.type === "contradiction"
                ? "bg-red-950/90 border border-red-800/50 text-red-200"
                : t.type === "stage"
                ? "bg-emerald-950/90 border border-emerald-700/50 text-emerald-200"
                : "bg-amber-950/90 border border-amber-800/50 text-amber-200",
            ].join(" ")}
          >
            {t.text}
          </div>
        ))}
      </div>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Tab Sidebar */}
        <aside className="w-14 border-r border-zinc-800 bg-zinc-950 flex flex-col items-center py-4 gap-4 z-20">
          <button
            onClick={() => setActiveTab("pinboard")}
            className={`p-2.5 rounded-xl transition-all ${activeTab === "pinboard" ? "bg-zinc-800 text-zinc-100 shadow-sm" : "text-zinc-600 hover:text-zinc-400"}`}
            title="Investigation Pinboard"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 5 4 4"/><path d="M21.5 12a9.5 9.5 0 1 1-19 0 9.5 9.5 0 0 1 19 0Z"/><path d="M12 7v10"/><path d="M7 12h10"/></svg>
          </button>
          <button
            onClick={() => setActiveTab("timeline")}
            className={`p-2.5 rounded-xl transition-all ${activeTab === "timeline" ? "bg-zinc-800 text-zinc-100 shadow-sm" : "text-zinc-600 hover:text-zinc-400"}`}
            title="Investigation Timeline"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="10"/></svg>
          </button>
        </aside>

        {/* Content Area */}
        <main className="relative flex-1 overflow-hidden">
          {activeTab === "pinboard" ? (
            <>
              {boardLoading && (
                <div className="absolute inset-0 flex items-center justify-center z-10 bg-zinc-950/50 backdrop-blur-sm">
                  <div className="flex flex-col items-center gap-3">
                    <div className="h-px w-12 animate-pulse bg-zinc-700" />
                    <span className="text-xs font-mono text-zinc-600 tracking-widest uppercase">Opening case file…</span>
                    <div className="h-px w-12 animate-pulse bg-zinc-700" />
                  </div>
                </div>
              )}
              {boardErr ? (
                <div className="flex h-full items-center justify-center p-6">
                  <div className="rounded-xl border border-red-900/40 bg-red-950/30 p-5 text-sm text-red-300 max-w-sm text-center">{boardErr}</div>
                </div>
              ) : sessionId ? (
                <Pinboard
                  ref={pinboardRef}
                  sessionId={sessionId}
                  onNodeClick={(nodeId, nodeData) => {
                    setSelectedPinNode({ id: nodeId, ...nodeData });
                    if ((nodeData.type as string) === "PERSON") {
                      setRole("suspect");
                      setPersonaId(nodeId);
                    }
                  }}
                />
              ) : null}

              {/* Slide-in node detail panel */}
              {selectedPinNode && (
                <div className="absolute right-4 top-4 w-72 bg-zinc-900/95 border border-zinc-700
                                rounded-xl p-4 z-50 shadow-2xl backdrop-blur-sm animate-fadeIn">
                  <button
                    onClick={() => setSelectedPinNode(null)}
                    className="absolute top-3 right-3 text-zinc-500 hover:text-white text-sm transition-colors"
                  >
                    ✕
                  </button>
                  <div
                    className="text-[10px] font-mono uppercase tracking-wider mb-1"
                    style={{ color: NODE_COLORS[(selectedPinNode.type as string) ?? "UNKNOWN"] ?? "#6b7280" }}
                  >
                    {selectedPinNode.type as string}
                  </div>
                  <h3 className="text-white font-bold text-sm leading-snug">
                    {selectedPinNode.label as string}
                  </h3>
                  {typeof selectedPinNode.description === "string" && selectedPinNode.description && (
                    <p className="text-zinc-400 text-xs mt-2 leading-relaxed line-clamp-6">
                      {selectedPinNode.description as string}
                    </p>
                  )}
                  {selectedPinNode.confidence != null && (
                    <div className="mt-3">
                      <div className="text-zinc-600 text-[10px] mb-1">
                        Confidence: {Math.round((selectedPinNode.confidence as number) * 100)}%
                      </div>
                      <div className="h-0.5 bg-zinc-800 rounded">
                        <div
                          className="h-full rounded transition-all"
                          style={{
                            width: `${(selectedPinNode.confidence as number) * 100}%`,
                            backgroundColor: NODE_COLORS[(selectedPinNode.type as string) ?? "UNKNOWN"] ?? "#ef4444",
                          }}
                        />
                      </div>
                    </div>
                  )}
                  {(selectedPinNode.type as string) === "PERSON" && (
                    <button
                      onClick={() => {
                        setRole("suspect");
                        setPersonaId(selectedPinNode.id as string);
                        setSelectedPinNode(null);
                      }}
                      className="mt-4 w-full bg-red-950 hover:bg-red-900 border border-red-800
                                 text-red-300 text-xs py-2 rounded font-mono tracking-wider transition-colors"
                    >
                      INTERROGATE
                    </button>
                  )}
                </div>
              )}

              {/* Stage description overlay (bottom left) */}
              {stageInfo && (
                <div className="absolute bottom-4 left-4 max-w-xs rounded-lg bg-zinc-900/90 border border-zinc-800 px-3 py-2 text-xs text-zinc-500">
                  <div className="text-zinc-400 font-mono text-[10px] uppercase tracking-widest mb-0.5">
                    Stage {stageInfo.current_stage} — {stageInfo.stage_name}
                  </div>
                  {stageInfo.stage_description}
                  {board && (
                    <div className="mt-1 text-zinc-600">🔍 {board.nodes.length} entities discovered</div>
                  )}
                </div>
              )}
            </>
          ) : (
            <TimelineView events={timelineEvents} />
          )}
        </main>

        {/* Right panel */}
        <aside className="flex w-[380px] flex-col border-l border-zinc-800 bg-zinc-950/80 overflow-hidden">
          {/* Evidence drawer */}
          {selectedNode && (
            <div className="border-b border-zinc-800 bg-zinc-900/60 p-4 animate-fadeIn">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className={`text-[10px] font-semibold uppercase tracking-wider mb-1 ${gs(selectedNode.type).label}`}>{selectedNode.type}</div>
                  <div className="text-sm font-semibold text-zinc-100">{selectedNode.name}</div>
                </div>
                <button onClick={() => setSelectedNode(null)} className="text-zinc-600 hover:text-zinc-400 text-xs">✕</button>
              </div>
              <p className="mt-2 text-xs text-zinc-400 leading-relaxed">{selectedNode.description}</p>
              <div className="mt-3 flex gap-2">
                <button onClick={() => { setInput(`Tell me more about ${selectedNode.name}`); setSelectedNode(null); }} className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
                  Ask co-detective →
                </button>
                {selectedNode.type.toLowerCase() === "evidence" && suspectNodes.length > 0 && (
                  <select
                    onChange={(e) => { if (e.target.value) presentEvidence(selectedNode.id, e.target.value); e.target.value = ""; }}
                    className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-[10px] text-zinc-400 outline-none"
                    defaultValue=""
                  >
                    <option value="" disabled>Present to suspect…</option>
                    {suspectNodes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                )}
              </div>
            </div>
          )}

          {/* Chat */}
          <div className="flex flex-1 flex-col overflow-hidden">
            <div className="flex items-center justify-between gap-2 border-b border-zinc-800 px-4 py-3">
              <div className="text-xs text-zinc-400 font-medium">
                Chat
                {stageInfo && (
                  <span className="ml-2 text-[10px] font-mono text-zinc-600">
                    [{stageInfo.stage_name}]
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <select value={role} onChange={e => { setRole(e.target.value); if (e.target.value === "co_detective") setPersonaId(null); }} className="rounded-lg border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 outline-none">
                  <option value="co_detective">🔍 Co-detective</option>
                  <option value="witness">👁 Witness</option>
                  <option value="suspect">🔴 Suspect</option>
                </select>
                {(role === "suspect" || role === "witness") && (
                  <select value={personaId ?? ""} onChange={e => setPersonaId(e.target.value || null)} className="rounded-lg border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 outline-none">
                    <option value="">Select persona…</option>
                    {board?.nodes
                      .filter(n => n.type.toLowerCase() === role)
                      .map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
                  </select>
                )}
              </div>
            </div>

            <div className="flex-1 space-y-2 overflow-auto p-4">
              {currentChat.length === 0 && (
                <div className="text-xs text-zinc-600 text-center mt-8 leading-relaxed">
                  Ask the {role.replace('_', '-')} a question.
                  <br /><br />
                  <span className="text-zinc-700">💡 Explore the scene. When you&apos;ve investigated enough, the <strong className="text-zinc-600">ADVANCE STAGE →</strong> button will appear.</span>
                </div>
              )}
              {currentChat.map((m, i) => (
                <div key={i} className={m.from === "you" ? "ml-auto max-w-[85%] rounded-xl bg-zinc-200 px-3.5 py-2.5 text-sm text-zinc-900" : "mr-auto max-w-[85%] rounded-xl bg-zinc-800/80 px-3.5 py-2.5 text-sm text-zinc-200 border border-zinc-700/50 whitespace-pre-line"}>
                  {m.text}
                </div>
              ))}
              {sending && (
                <div className="mr-auto rounded-xl bg-zinc-800/80 border border-zinc-700/50 px-4 py-3">
                  <div className="flex gap-1">
                    {[0, 0.15, 0.3].map((d, i) => (
                      <span key={i} className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: `${d}s` }} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-zinc-800 p-3 flex gap-2">
              <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter") void send(); }} placeholder="Ask about the case…" className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-zinc-500" />
              <button onClick={() => void send()} disabled={sending} className="rounded-lg bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-900 hover:bg-white disabled:opacity-40 transition-colors">→</button>
            </div>
          </div>
        </aside>
      </div>

      {/* Notes panel */}
      {notesOpen && (
        <div className="absolute bottom-0 left-0 right-[380px] border-t border-zinc-800 bg-zinc-900/95 p-4 backdrop-blur-sm animate-fadeIn">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-zinc-400">📝 Investigation Notes</span>
            <span className="text-xs text-zinc-600">{notesSaved ? "Saved" : "Saving…"}</span>
          </div>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Record your observations…" rows={4} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 outline-none placeholder:text-zinc-700 resize-none focus:border-zinc-600" />
        </div>
      )}

      {/* Conclusion modal */}
      {concludeOpen && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl animate-fadeIn">
            {concludeResult ? (
              /* Results */
              <div>
                <h2 className="text-lg font-semibold text-zinc-100 mb-4">🏁 Case Evaluation</h2>
                <div className="flex items-center gap-4 mb-4">
                  <div className="text-4xl font-bold text-zinc-100">{concludeResult.percentage}%</div>
                  <div className="text-sm text-zinc-400">{concludeResult.score}/{concludeResult.max_score} points</div>
                </div>
                <pre className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed mb-4">{concludeResult.feedback}</pre>
                <div className="rounded-lg bg-zinc-800 p-3 mb-4">
                  <div className="text-xs text-zinc-500 mb-1">Official Verdict</div>
                  <div className="text-sm text-zinc-200">{concludeResult.official_verdict}</div>
                </div>
                <button onClick={() => { setConcludeOpen(false); setConcludeResult(null); }} className="w-full rounded-lg bg-zinc-100 py-2 text-sm font-medium text-zinc-900 hover:bg-white">Close</button>
              </div>
            ) : (
              /* Form */
              <div>
                <div className="flex items-center justify-between mb-5">
                  <h2 className="text-base font-semibold text-zinc-100">🏁 Submit Your Conclusion</h2>
                  <button onClick={() => setConcludeOpen(false)} className="text-zinc-500 hover:text-zinc-300 text-sm">✕</button>
                </div>
                {currentStage < 5 && (
                  <div className="mb-4 rounded-lg bg-amber-950/40 border border-amber-800/30 px-4 py-3 text-xs text-amber-400">
                    ⚠️ You are on Stage {currentStage}/6. For a full investigation, advance through all stages before submitting.
                  </div>
                )}
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-zinc-500 mb-1.5 block">Who did it?</label>
                    {suspectNodes.length > 0 ? (
                      <select value={conclusion.killer} onChange={e => setConclusion({ ...conclusion, killer: e.target.value })} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none">
                        <option value="">Select suspect…</option>
                        {suspectNodes.map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
                      </select>
                    ) : (
                      <input value={conclusion.killer} onChange={e => setConclusion({ ...conclusion, killer: e.target.value })} placeholder="Name the perpetrator…" className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600" />
                    )}
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 mb-1.5 block">Motive</label>
                    <textarea value={conclusion.motive} onChange={e => setConclusion({ ...conclusion, motive: e.target.value })} placeholder="Why did they do it?" rows={3} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 resize-none" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 mb-1.5 block">Method (optional)</label>
                    <input value={conclusion.method} onChange={e => setConclusion({ ...conclusion, method: e.target.value })} placeholder="How was it done?" className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600" />
                  </div>
                </div>
                <div className="mt-6 flex gap-3">
                  <button onClick={() => void submitConclusion()} disabled={!conclusion.killer} className="flex-1 rounded-lg bg-zinc-100 py-2 text-sm font-medium text-zinc-900 hover:bg-white disabled:opacity-40 transition-colors">Submit Deduction</button>
                  <button onClick={() => setConcludeOpen(false)} className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
