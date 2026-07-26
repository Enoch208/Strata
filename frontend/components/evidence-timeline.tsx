import type { ClaimEvent, Finding, Shot } from "@/lib/types";
import { TimelineCard } from "./timeline-card";

type Props = {
  events: ClaimEvent[];
  findings: Finding[];
  shots: Shot[];
  selectedEventId: string | null;
  highlightedEventIds: string[];
  reelEventIds: string[];
  onSelect: (eventId: string) => void;
  onToggleReel: (eventId: string) => void;
};

export function EvidenceTimeline({
  events,
  findings,
  shots,
  selectedEventId,
  highlightedEventIds,
  reelEventIds,
  onSelect,
  onToggleReel,
}: Props) {
  return (
    <aside className="flex h-full min-h-[520px] flex-col bg-black/30">
      <div className="panel-toolbar">
        <span>Chronological trail</span>
        <span className="tabular-nums text-white/35">{events.length} events</span>
      </div>
      <div className="timeline-scroll flex-1 space-y-3 overflow-y-auto p-3">
        {events.map((event) => (
          <TimelineCard
            key={event.event_id}
            event={event}
            shot={shots.find((shot) => shot.event_id === event.event_id)}
            finding={findings.find((finding) =>
              finding.event_ids.includes(event.event_id),
            )}
            selected={selectedEventId === event.event_id}
            highlighted={highlightedEventIds.includes(event.event_id)}
            inReel={reelEventIds.includes(event.event_id)}
            onSelect={() => onSelect(event.event_id)}
            onToggleReel={() => onToggleReel(event.event_id)}
          />
        ))}
      </div>
    </aside>
  );
}
