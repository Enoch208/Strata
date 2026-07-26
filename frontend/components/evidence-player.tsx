import type { ClaimEvent, Shot } from "@/lib/types";
import { formatDate, formatWindow } from "@/lib/format";
import { Icon } from "./icon";
import { MediaPlayer } from "./media-player";

type Props = {
  event: ClaimEvent | null;
  shot: Shot | null;
};

export function EvidencePlayer({ event, shot }: Props) {
  if (!event) {
    return (
      <section className="flex h-full min-h-[520px] flex-col bg-black/20">
        <div className="panel-toolbar">
          <span>Evidence player</span>
          <span className="text-white/30">No event selected</span>
        </div>
        <div className="grid flex-1 place-items-center p-8 text-center">
          <div>
            <span className="player-empty-icon mx-auto">
              <Icon name="play" className="size-5" />
            </span>
            <p className="mt-4 text-sm text-white/55">
              Select an event to inspect its source moment.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="flex h-full min-h-[520px] flex-col bg-black/20">
      <div className="panel-toolbar">
        <div className="min-w-0">
          <span>Evidence player</span>
          <span className="mx-2 text-white/20">•</span>
          <span className="truncate text-white/45">
            {shot?.video_title ?? event.video_id}
          </span>
        </div>
        <span className="status-pill status-ready shrink-0">
          <span className="status-dot" />
          Source locked
        </span>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-3 sm:p-5">
        <div className="rounded-2xl border border-white/10 bg-black/40 p-2.5 shadow-2xl">
          <MediaPlayer
            streamUrl={shot?.stream_url ?? null}
            playerUrl={shot?.player_url ?? null}
            title={shot?.video_title ?? event.claim_text}
          />
        </div>

        <div className="detail-card">
          <p className="detail-label">Now inspecting</p>
          <p className="mt-2 text-sm leading-6 text-white/75">{event.claim_text}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-white/40">
            <span>{event.source_organization}</span>
            <span>·</span>
            <span>{formatDate(event.source_date)}</span>
            <span>·</span>
            <span className="tabular-nums">
              {formatWindow(event.start, event.end)}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
