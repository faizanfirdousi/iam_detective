"use client";

import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  useNodesState,
  useEdgesState,
  updateEdge,
  type Node,
  type Edge,
  type NodeProps,
  type OnNodesChange,
  type OnEdgesChange,
  type Connection,
  type Viewport,
} from "reactflow";
import "reactflow/dist/style.css";
import { forwardRef, useCallback, useEffect, useMemo, useImperativeHandle, useRef, useState } from "react";
import DetectiveNode from "./nodes/DetectiveNode";
import LockedNode from "./nodes/LockedNode";

import { api } from "@/lib/api";

// ── Persistence Helpers ────────────────────────────────────────────────────────

interface StoredGraphState {
  nodes: Record<string, { x: number; y: number }>;
  edges: Edge[];
  viewport?: Viewport;
}

const saveGraphState = (sessionId: string, nodes: Node[], edges: Edge[], viewport?: Viewport) => {
  // Only save if we have nodes (avoid saving empty state on initial loads/errors)
  if (nodes.length === 0) return;

  const nodePositions: Record<string, { x: number; y: number }> = {};
  nodes.forEach((node) => {
    nodePositions[node.id] = node.position;
  });

  const state: StoredGraphState = {
    nodes: nodePositions,
    edges,
    viewport: viewport,
  };
  
  // Fire and forget (backend handles persistence)
  api.saveGraphState(sessionId, state).catch(() => {});
};

// ── Type colours ───────────────────────────────────────────────────────────────
export const NODE_COLORS: Record<string, string> = {
  PERSON:        "#ef4444", // red
  EVIDENCE:      "#f59e0b", // amber
  LOCATION:      "#3b82f6", // blue
  EVENT:         "#22c55e", // green
  TIMELINE:      "#a855f7", // purple
  ORGANIZATION:  "#f97316", // orange
  UNKNOWN:       "#6b7280", // gray
};

// ── Layout helper — radial arrangement ────────────────────────────────────────
function buildFlowGraph(
  apiNodes: Record<string, unknown>[],
  apiEdges: Record<string, unknown>[]
): { nodes: Node[]; edges: Edge[] } {
  const total = apiNodes.length;
  const radiusBase = Math.min(280 + total * 12, 650);

  const nodes: Node[] = apiNodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / total;
    const r = radiusBase + (i % 3) * 40; // slight stagger to reduce overlap
    const color = NODE_COLORS[(n.type as string) ?? "UNKNOWN"] ?? NODE_COLORS.UNKNOWN;
    return {
      id: n.id as string,
      type: (n.locked ? "locked" : (["PERSON", "EVIDENCE", "LOCATION", "EVENT", "TIMELINE", "ORGANIZATION"].includes(n.type as string) ? (n.type as string) : "UNKNOWN")),
      position: {
        x: 600 + r * Math.cos(angle),
        y: 420 + r * Math.sin(angle),
      },
      data: { ...n, color },
    };
  });

  const edges: Edge[] = (apiEdges as Record<string, unknown>[]).map((e, i) => {
    const confidence = (e.confidence as number) ?? 0.7;
    const source = (e.source ?? e.from) as string;
    const target = (e.target ?? e.to) as string;
    const rel = typeof e.relationship === "string" ? e.relationship.toLowerCase().replace(/[^a-z0-9]/g, "_") : "rel";
    return {
      id: `e-${source}-${target}-${rel}-${i}`,
      source,
      target,
      label: typeof e.relationship === "string"
        ? e.relationship.replace(/_/g, " ").toLowerCase()
        : undefined,
      type: "straight",
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: confidence > 0.7 ? "#ef4444" : "#f97316",
      },
      style: {
        stroke: confidence > 0.7 ? "#ef4444" : "#f97316",
        strokeWidth: confidence > 0.7 ? 2 : 1,
        strokeDasharray: confidence < 0.5 ? "6,4" : undefined,
        opacity: 0.4 + confidence * 0.6,
      },
      labelStyle: {
        fill: "#a1a1aa",
        fontSize: 9,
        fontFamily: "monospace",
      },
      labelBgStyle: { fill: "#18181b", fillOpacity: 0.85 },
    };
  });

  return { nodes, edges };
}

// ── Public API exposed via ref ─────────────────────────────────────────────────
export interface PinboardHandle {
  refresh: () => Promise<void>;
}

interface PinboardProps {
  sessionId: string;
  onNodeClick?: (nodeId: string, nodeData: Record<string, unknown>) => void;
}

// Empty string ensures client-side fetches use the current origin's /api route
const API_BASE = "";

// ── Component ──────────────────────────────────────────────────────────────────
const Pinboard = forwardRef<PinboardHandle, PinboardProps>(
  ({ sessionId, onNodeClick }, ref) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [viewport, setViewport] = useState<Viewport | undefined>(undefined);
    const edgeUpdateSuccessful = useRef(true);

    const nodeTypesMemo = useMemo(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const node: React.ComponentType<NodeProps<any>> = DetectiveNode as any;
      return {
        PERSON:       node,
        EVIDENCE:     node,
        LOCATION:     node,
        EVENT:        node,
        TIMELINE:     node,
        ORGANIZATION: node,
        UNKNOWN:      node,
        locked:       LockedNode as any,
      };
    }, []);

    const fetchGraph = useCallback(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/graph`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.graph) return;

        const { nodes: fn, edges: fe } = buildFlowGraph(
          data.graph.nodes as Record<string, unknown>[],
          data.graph.edges as Record<string, unknown>[]
        );

        // Fetch persisted state from DB
        const { graph_state: saved } = await api.getGraphState(sessionId);
        
        if (saved && saved.nodes) {
          // Merge node positions
          const mergedNodes = fn.map((node) => {
            if (saved.nodes[node.id]) {
              return { ...node, position: saved.nodes[node.id] };
            }
            return node;
          });
          setNodes(mergedNodes);

          // For edges, use saved modifications where available, but keep API as source of existence
          const savedEdgeMap = new Map((saved.edges || []).map((e: Edge) => [e.id, e]));
          const mergedEdges = fe.map(edge => {
            if (savedEdgeMap.has(edge.id)) {
              return { ...edge, ...savedEdgeMap.get(edge.id) };
            }
            return edge;
          });
          
          setEdges(mergedEdges);
          
          if (saved.viewport && !viewport) {
            setViewport(saved.viewport);
          }
        } else {
          setNodes(fn);
          setEdges(fe);
        }
      } catch (err) {
        console.error("[Pinboard] fetch failed:", err);
      }
    }, [sessionId, setNodes, setEdges, viewport]);

    // Handle callbacks for persistence
    const onNodeDragStop = useCallback(() => {
      saveGraphState(sessionId, nodes, edges, viewport);
    }, [sessionId, nodes, edges, viewport]);

    const onMoveEnd = useCallback((_: unknown, vp: Viewport) => {
      setViewport(vp);
      saveGraphState(sessionId, nodes, edges, vp);
    }, [sessionId, nodes, edges]);

    const onEdgeUpdateStart = useCallback(() => {
      edgeUpdateSuccessful.current = false;
    }, []);

    const onEdgeUpdate = useCallback(
      (oldEdge: Edge, newConnection: Connection) => {
        edgeUpdateSuccessful.current = true;
        setEdges((els) => {
          const updated = updateEdge(oldEdge, newConnection, els);
          saveGraphState(sessionId, nodes, updated, viewport);
          return updated;
        });
      },
      [sessionId, nodes, viewport, setEdges]
    );

    const onEdgeUpdateEnd = useCallback(
      (_: MouseEvent | TouchEvent, edge: Edge) => {
        if (!edgeUpdateSuccessful.current) {
          setEdges((eds) => {
            const filtered = eds.filter((e) => e.id !== edge.id);
            saveGraphState(sessionId, nodes, filtered, viewport);
            return filtered;
          });
        }
        edgeUpdateSuccessful.current = true;
      },
      [sessionId, nodes, viewport, setEdges]
    );

    const onNodesDelete = useCallback(() => {
      saveGraphState(sessionId, nodes, edges, viewport);
    }, [sessionId, nodes, edges, viewport]);

    const onEdgesDelete = useCallback(() => {
      saveGraphState(sessionId, nodes, edges, viewport);
    }, [sessionId, nodes, edges, viewport]);

    // Expose refresh() to parent via ref
    useImperativeHandle(ref, () => ({ refresh: fetchGraph }));

    useEffect(() => {
      fetchGraph();
      // Poll every 30 s to pick up AI enrichment completing in the background
      const timer = setInterval(fetchGraph, 30_000);
      return () => clearInterval(timer);
    }, [fetchGraph]);

    return (
      <div className="w-full h-full bg-zinc-950 rounded-lg border border-zinc-800">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          defaultViewport={viewport}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStop={onNodeDragStop}
          onNodesDelete={onNodesDelete}
          onEdgesDelete={onEdgesDelete}
          onMoveEnd={onMoveEnd}
          onEdgeUpdate={onEdgeUpdate}
          onEdgeUpdateStart={onEdgeUpdateStart}
          onEdgeUpdateEnd={onEdgeUpdateEnd}
          nodeTypes={nodeTypesMemo}
          onNodeClick={(_, node) => {
            if (!node.data?.locked) {
              onNodeClick?.(node.id, node.data as Record<string, unknown>);
            }
          }}
          fitView={!viewport}
          minZoom={0.15}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#27272a" gap={24} />
          <Controls className="!bg-zinc-900 !border-zinc-700" />
          <MiniMap
            nodeColor={(n) => (n.data?.color as string) ?? "#6b7280"}
            className="!bg-zinc-900 !border-zinc-800"
            maskColor="rgba(0,0,0,0.75)"
          />
        </ReactFlow>
      </div>
    );
  }
);

Pinboard.displayName = "Pinboard";
export default Pinboard;
