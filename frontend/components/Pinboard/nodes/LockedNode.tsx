import { Handle, Position } from "reactflow";

export default function LockedNode() {
  return (
    <div
      className="rounded-lg border-2 border-dashed border-zinc-700 p-3
                  w-28 bg-zinc-950 opacity-40 select-none cursor-not-allowed"
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="text-xl text-center">🔒</div>
      <div className="text-zinc-600 text-xs font-mono text-center mt-1">???</div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}
