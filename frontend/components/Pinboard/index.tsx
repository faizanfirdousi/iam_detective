"use client";

import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { forwardRef, useCallback, useEffect, useImperativeHandle } from "react";
import DetectiveNode from "./nodes/DetectiveNode";
import LockedNode from "./nodes/LockedNode";

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

// ── ReactFlow node type registry ──────────────────────────────────────────────
// Using a cast to ComponentType<NodeProps> for each entry satisfies ReactFlow's NodeTypes.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyNodeComponent = React.ComponentType<NodeProps<any>>;
const nodeTypes: Record<string, AnyNodeComponent> = {
  PERSON:       DetectiveNode as AnyNodeComponent,
  EVIDENCE:     DetectiveNode as AnyNodeComponent,
  LOCATION:     DetectiveNode as AnyNodeComponent,
  EVENT:        DetectiveNode as AnyNodeComponent,
  TIMELINE:     DetectiveNode as AnyNodeComponent,
  ORGANIZATION: DetectiveNode as AnyNodeComponent,
  UNKNOWN:      DetectiveNode as AnyNodeComponent,
  locked:       LockedNode as AnyNodeComponent,
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
      type: (n.locked ? "locked" : ((n.type as string) in nodeTypes ? (n.type as string) : "UNKNOWN")),
      position: {
        x: 600 + r * Math.cos(angle),
        y: 420 + r * Math.sin(angle),
      },
      data: { ...n, color },
    };
  });

  const edges: Edge[] = (apiEdges as Record<string, unknown>[]).map((e, i) => {
    const confidence = (e.confidence as number) ?? 0.7;
    return {
      id: `e-${i}`,
      source: (e.source ?? e.from) as string,
      target: (e.target ?? e.to) as string,
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

// Mirrors the base URL logic from lib/api.ts
const API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000")
    : "http://localhost:8000";

// ── Component ──────────────────────────────────────────────────────────────────
const Pinboard = forwardRef<PinboardHandle, PinboardProps>(
  ({ sessionId, onNodeClick }, ref) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

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
        setNodes(fn);
        setEdges(fe);
      } catch (err) {
        console.error("[Pinboard] fetch failed:", err);
      }
    }, [sessionId, setNodes, setEdges]);

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
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onNodeClick={(_, node) => {
            if (!node.data?.locked) {
              onNodeClick?.(node.id, node.data as Record<string, unknown>);
            }
          }}
          fitView
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
