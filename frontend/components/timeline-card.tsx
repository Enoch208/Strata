import type { ClaimEvent, Finding, Shot } from "@/lib/types";
import { formatDate, formatWindow, labelTone, words } from "@/lib/format";
import { Icon } from "./icon";

type Props = {
  event: ClaimEvent;
  shot: Shot | undefined;
  finding: Finding | undefined;
  selected: boolean;
  highlighted: boolean;
  inReel: boolean;
  onSelect: () => void;
  onToggleReel: () => void;
};

export function TimelineCard({
  event,
  shot,
  finding,
  selected,
  highlighted,
  inReel,
  onSelect,
  onToggleReel,
}: Props) {
  const playable = Boolean(shot?.stream_url);
  const tone = finding ? labelTone[finding.label] : "tone-neutral";

  return (
    <article
      id={`event-${event.event_id}`}
      className={`timeline-card ${tone} ${selected ? "timeline-selected" : ""} ${
        highlighted ? "timeline-highlighted" : ""
      }`}
    >
      <button onClick={onSelect} className="block w-full text-left">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="tabular-nums text-[11px] text-white/40">
              {formatDate(event.source_date)} ·{" "}
              {formatWindow(event.start, event.end)}
            </p>
            <span className={`finding-badge mt-2 ${tone}`}>
              {words(finding?.label ?? event.claim_type)}
            </span>
          </div>
          <Icon
            name="chevron"
            className={`mt-1 size-4 shrink-0 transition ${
              selected ? "translate-x-1 text-white" : "text-white/25"
            }`}
          />
        </div>
        <h3 className="mt-3 text-[15px] font-medium leading-5 tracking-tight text-white/90">
          {finding?.title ?? event.claim_text}
        </h3>
        <p className="mt-2 line-clamp-3 text-xs font-light leading-5 text-white/45">
          {finding?.summary ?? event.claim_text}
        </p>
        <div className="mt-3 flex items-center gap-2 text-[10px] text-white/35">
          <span>{event.speaker_name ?? event.speaker_role ?? "Speaker not identified"}</span>
          <span>·</span>
          <span>{words(finding?.confidence ?? event.certainty)}</span>
        </div>
      </button>

      <div className="mt-4 flex items-center gap-2 border-t border-white/8 pt-3">
        {playable ? (
          <button onClick={onSelect} className="event-action">
            <Icon name="play" className="size-3.5" />
            Play evidence
          </button>
        ) : (
          <span className="event-unavailable">
            <Icon name="film" className="size-3.5" />
            Playback unavailable
          </span>
        )}
        {playable ? (
          <button
            onClick={onToggleReel}
            className={`event-action ml-auto ${inReel ? "event-action-active" : ""}`}
            aria-pressed={inReel}
          >
            <Icon name={inReel ? "check" : "plus"} className="size-3.5" />
            {inReel ? "In reel" : "Add to reel"}
          </button>
        ) : null}
      </div>
      {finding?.review_reason ? (
        <p className="mt-3 rounded-lg bg-amber-400/8 p-2 text-[10px] leading-4 text-amber-200/65">
          Needs review: {finding.review_reason}
        </p>
      ) : null}
    </article>
  );
}
