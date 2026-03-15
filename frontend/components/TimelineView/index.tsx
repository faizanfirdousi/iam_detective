"use client";

import { TimelineEvent } from "@/lib/api";
import { format } from "date-fns";

export default function TimelineView({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <div className="text-zinc-600 text-sm mb-2 font-mono uppercase tracking-widest">NO HISTORY RECORDED</div>
        <p className="text-zinc-500 text-xs max-w-xs">Start investigating to see your progress here.</p>
      </div>
    );
  }

  // Group events by stage
  const stages = Array.from(new Set(events.map(e => e.stage))).sort((a, b) => b - a);

  return (
    <div className="h-full overflow-y-auto p-6 bg-zinc-950/50">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-lg font-semibold text-zinc-100">Investigation Timeline</h2>
          <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest">
            {events.length} EVENTS RECORDED
          </div>
        </div>

        <div className="space-y-12">
          {stages.map(stageNum => (
            <div key={stageNum} className="relative">
              {/* Stage Header */}
              <div className="sticky top-0 z-10 py-2 mb-6 bg-zinc-950/80 backdrop-blur-sm border-b border-zinc-800 flex items-center justify-between">
                <h3 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-widest">
                  Stage {stageNum}
                </h3>
              </div>

              {/* Events for this stage */}
              <div className="space-y-6 ml-4 border-l border-zinc-800 pl-8 relative">
                {events
                  .filter(e => e.stage === stageNum)
                  .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                  .map((event, i) => (
                    <div key={event.id} className="relative group">
                      {/* Timeline dot */}
                      <div className={`absolute -left-[37px] top-1.5 h-4 w-4 rounded-full border-2 border-zinc-950 shadow-sm transition-transform group-hover:scale-125 ${
                        event.type === 'discovery' ? 'bg-amber-500' :
                        event.type === 'contradiction' ? 'bg-red-500' :
                        event.type === 'stage_advance' ? 'bg-emerald-500' :
                        'bg-zinc-500'
                      }`} />

                      <div className="flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-zinc-200">{event.title}</span>
                          <span className="text-[10px] font-mono text-zinc-600">
                            {format(new Date(event.timestamp), "HH:mm")}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 leading-relaxed italic">
                          {event.description}
                        </p>
                        
                        {/* Meta info / labels */}
                        <div className="mt-1 flex flex-wrap gap-2">
                          <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border ${
                            event.type === 'discovery' ? 'border-amber-900/40 text-amber-500 bg-amber-950/20' :
                            event.type === 'contradiction' ? 'border-red-900/40 text-red-500 bg-red-950/20' :
                            event.type === 'stage_advance' ? 'border-emerald-900/40 text-emerald-500 bg-emerald-950/20' :
                            'border-zinc-800 text-zinc-500 bg-zinc-900/50'
                          }`}>
                            {event.type.replace('_', ' ')}
                          </span>
                          {typeof event.meta.trigger === 'string' && (
                            <span className="text-[9px] font-mono text-zinc-600 px-1.5 py-0.5 rounded border border-zinc-800">
                              TRIGGER: &ldquo;{event.meta.trigger}&rdquo;
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
