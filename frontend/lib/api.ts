// During build / SSR (server-side), relative paths don't work — we need an absolute URL.
// On DigitalOcean, process.env.APP_URL is automatically injected at runtime.
// On the client side, empty string works because Next.js proxies /api to the backend.
const API_BASE =
  typeof window === "undefined"
    ? `${process.env.APP_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/api`
    : "";


// ── Types ────────────────────────────────────────────────────────────────────

export type CaseDifficulty = { forensics: number; witnesses: number; complexity: number };

export interface CaseListItem {
  id: string;
  title: string;
  subtitle: string;
  status: string;
  hero_image_url: string | null;
  year: number | null;
  location: string | null;
  difficulty: CaseDifficulty | null;
}

export interface CaseDetail {
  id: string;
  title: string;
  status: string;
  opening_lines: string[];
  sources: string[];
  year: number | null;
  location: string | null;
  intro_slides: CaseIntroSlide[];
}

export interface CaseIntroSlide {
  page: number;
  text: string;
  image_prompt: string;
}

export interface LinkNode {
  id: string;
  type: string;
  name: string;
  description: string;
  image_url?: string | null;
  revealed_at_stage?: number;
}

export interface LinkEdge {
  from: string;
  to: string;
  label: string;
  revealed_at_stage?: number;
}

export interface LinkBoard {
  stage: number;
  nodes: LinkNode[];
  edges: LinkEdge[];
}

export type ChatRole = "co_detective" | "witness" | "suspect";

export interface ChatRequest {
  role: ChatRole;
  message: string;
  stage?: number;
  persona_id?: string | null;
}

export interface ChatResponse {
  role: string;
  reply: string;
  stage_suggestion?: number | null;
}

// ── Session types (Investigation Engine) ───────────────────────────────────

export interface SessionCreateResponse {
  session_id: string;
  case_id: string;
  discovered_entities: string[];
}

export interface SessionBoard {
  session_id: string;
  case_id: string;
  stage: number;
  stage_name: string;
  can_advance: boolean;
  nodes: LinkNode[];
  edges: LinkEdge[];
  newly_unlocked: { id: string; name: string; type: string }[];
  contradictions: { character_id?: string; id: string; claim: string; confrontation_prompt?: string }[];
}

export interface SessionChatRequest {
  message: string;
  role: string;
  persona_id?: string | null;
}

export interface SessionChatResponse {
  reply: string;
  role: string;
  newly_unlocked: { id: string; name: string; type: string }[];
  contradictions: { character_id?: string; id: string; claim: string; confrontation_prompt?: string }[];
}

export interface ConcludeRequest {
  killer: string;
  motive: string;
  method?: string;
}

export interface ConcludeResponse {
  score: number;
  max_score: number;
  percentage: number;
  feedback: string;
  official_verdict: string;
  entities_discovered: number;
  total_entities: number;
}

export interface StageInfo {
  current_stage: number;
  stage_name: string;
  stage_description: string;
  completed_stages: number[];
  can_advance: boolean;
  requirements_met: Record<string, boolean>;
}

export interface StageAdvanceResponse {
  advanced: boolean;
  new_stage: number;
  stage_name: string;
  stage_description: string;
  newly_unlocked_entities: { id: string; name: string; type: string }[];
  graph_event: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function fetchJSON<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`api_error:${res.status}:${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── API client ───────────────────────────────────────────────────────────────

export const api = {
  // --- Cases (static) ---
  listCases: () => fetchJSON<CaseListItem[]>("/api/cases"),
  getCase: (id: string) => fetchJSON<CaseDetail>(`/api/cases/${id}`),
  getIntroSlides: (id: string) => fetchJSON<CaseIntroSlide[]>(`/api/cases/${id}/intro`),

  // --- Legacy (no session) ---
  getLinkBoard: (id: string, stage = 1) =>
    fetchJSON<LinkBoard>(`/api/cases/${id}/linkboard?stage=${stage}`),

  chat: (id: string, req: ChatRequest) =>
    fetchJSON<ChatResponse>(`/api/cases/${id}/chat`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  // --- Session-based (Investigation Engine) ---
  createSession: (caseId: string) =>
    fetchJSON<SessionCreateResponse>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId }),
    }),

  getSessionBoard: (sessionId: string) =>
    fetchJSON<SessionBoard>(`/api/sessions/${sessionId}/board`),

  sessionChat: (sessionId: string, req: SessionChatRequest) =>
    fetchJSON<SessionChatResponse>(`/api/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  presentEvidence: (sessionId: string, evidenceId: string, suspectId: string) =>
    fetchJSON<SessionChatResponse>(`/api/sessions/${sessionId}/present-evidence`, {
      method: "POST",
      body: JSON.stringify({ evidence_id: evidenceId, suspect_id: suspectId }),
    }),

  getContradictions: (sessionId: string) =>
    fetchJSON<{ contradictions_found: string[]; new_contradictions: unknown[] }>(
      `/api/sessions/${sessionId}/contradictions`
    ),

  conclude: (sessionId: string, req: ConcludeRequest) =>
    fetchJSON<ConcludeResponse>(`/api/sessions/${sessionId}/conclude`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  satisfyGate: (sessionId: string, gateName: string) =>
    fetchJSON<{ gate: string; newly_unlocked: { id: string; name: string; type: string }[] }>(
      `/api/sessions/${sessionId}/gate?gate_name=${encodeURIComponent(gateName)}`,
      { method: "POST" }
    ),

  getStage: (sessionId: string) =>
    fetchJSON<StageInfo>(`/api/sessions/${sessionId}/stage`),

  advanceStage: (sessionId: string) =>
    fetchJSON<StageAdvanceResponse>(`/api/sessions/${sessionId}/stage/advance`, {
      method: "POST",
    }),
};
