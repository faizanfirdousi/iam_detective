import { Handle, Position } from "reactflow";

const ICONS: Record<string, string> = {
  PERSON:       "👤",
  EVIDENCE:     "🔍",
  LOCATION:     "📍",
  EVENT:        "📋",
  TIMELINE:     "⏱",
  ORGANIZATION: "🏛",
  UNKNOWN:      "●",
};

interface DetectiveNodeData {
  label: string;
  type: string;
  description?: string;
  imageUrl?: string;
  image_url?: string;
  confidence?: number;
  importance?: string;
  color?: string;
  locked?: boolean;
}

export default function DetectiveNode({ data }: { data: DetectiveNodeData }) {
  const imgUrl = data.imageUrl || data.image_url;
  const confidence = data.confidence ?? 1;
  const color = data.color ?? "#6b7280";

  return (
    <div
      className="relative rounded-lg border-2 p-3 w-36 cursor-pointer select-none
                 bg-zinc-900 hover:bg-zinc-800 transition-all duration-200"
      style={{
        borderColor: color,
        boxShadow:
          confidence > 0.75
            ? `0 0 14px ${color}55, 0 0 4px ${color}33`
            : "none",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />

      {imgUrl ? (
        <img
          src={imgUrl}
          alt={data.label}
          className="w-10 h-10 rounded-full object-cover mx-auto mb-2 border border-zinc-700"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ) : (
        <div className="text-2xl text-center mb-1">
          {ICONS[data.type] ?? ICONS.UNKNOWN}
        </div>
      )}

      <div className="text-white text-xs font-bold text-center leading-tight line-clamp-2">
        {data.label}
      </div>

      {data.importance === "HIGH" && (
        <div
          className="mt-1 text-center text-[9px] px-1 rounded font-mono uppercase tracking-wider"
          style={{ backgroundColor: `${color}22`, color }}
        >
          KEY
        </div>
      )}

      {/* Confidence bar */}
      <div className="mt-2 h-0.5 rounded bg-zinc-700">
        <div
          className="h-full rounded transition-all duration-500"
          style={{
            width: `${confidence * 100}%`,
            backgroundColor: color,
          }}
        />
      </div>

      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}
