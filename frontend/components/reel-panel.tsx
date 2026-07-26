import type { ClaimEvent, ReelRef, ReelState, Shot } from "@/lib/types";
import { formatDate, formatTime, formatWindow } from "@/lib/format";
import { PrimaryButton } from "./button";
import { Icon } from "./icon";
import { MediaPlayer } from "./media-player";

type Props = {
  events: ClaimEvent[];
  shots: Shot[];
  selectedEventIds: string[];
  reel: ReelRef;
  state: ReelState;
  error: string | null;
  onGenerate: () => void;
};

export function ReelPanel({
  events,
  shots,
  selectedEventIds,
  reel,
  state,
  error,
  onGenerate,
}: Props) {
  const selected = events.filter((event) =>
    selectedEventIds.includes(event.event_id),
  );

  return (
    <section
      id="evidence-reels"
      className="glass-panel animate-on-scroll overflow-hidden"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            <span className="tabular-nums text-white/80">04</span>
            <span className="eyebrow-rule" />
            <span>Playable evidence reel</span>
          </p>
          <h2 className="mt-3 text-3xl font-light tracking-tight text-white">
            Build the chronological cut
          </h2>
          <p className="mt-2 text-sm text-white/40">
            Only source shots selected from the accepted timeline are compiled.
          </p>
        </div>
        <PrimaryButton
          onClick={onGenerate}
          disabled={selectedEventIds.length === 0 || state === "generating"}
        >
          <Icon name="film" />
          {state === "generating"
            ? "Generating reel…"
            : state === "failed"
              ? "Retry reel"
              : "Generate evidence reel"}
        </PrimaryButton>
      </div>

      <div className="grid border-t border-white/10 lg:grid-cols-12">
        <div className="p-4 sm:p-6 lg:col-span-5">
          <div className="flex items-center justify-between">
            <p className="detail-label">Selected sequence</p>
            <span className="tabular-nums text-[11px] text-white/35">
              {selected.length} shots
            </span>
          </div>
          <div className="mt-4 space-y-2">
            {selected.length ? (
              selected.map((event, index) => {
                const shot = shots.find((item) => item.event_id === event.event_id);
                return (
                  <div key={event.event_id} className="reel-event">
                    <span className="reel-order tabular-nums">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-xs text-white/70">
                        {shot?.video_title ?? event.claim_text}
                      </p>
                      <p className="mt-1 tabular-nums text-[10px] text-white/30">
                        {formatDate(event.source_date)} ·{" "}
                        {formatWindow(event.start, event.end)}
                      </p>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="rounded-xl border border-dashed border-white/10 p-5 text-center text-xs text-white/35">
                Add playable events from the timeline to build a reel.
              </p>
            )}
          </div>
        </div>

        <div className="border-t border-white/10 bg-black/20 p-4 sm:p-6 lg:col-span-7 lg:border-l lg:border-t-0">
          {state === "generating" ? (
            <div className="player-empty aspect-video">
              <span className="processing-mark">
                <Icon name="film" className="size-5" />
              </span>
              <p className="mt-4 text-sm text-white/60">
                Generating evidence reel
              </p>
            </div>
          ) : state === "failed" ? (
            <div className="player-empty aspect-video">
              <span className="player-empty-icon">
                <Icon name="film" className="size-6" />
              </span>
              <p className="mt-4 text-sm font-medium text-white">
                Reel generation failed
              </p>
              <p className="mt-2 max-w-sm text-center text-xs leading-5 text-white/40">
                {error ?? reel.error ?? "The archive service did not produce a reel."}
              </p>
              <button
                onClick={onGenerate}
                className="secondary-button secondary-button-compact mt-4"
              >
                <Icon name="refresh" />
                Retry
              </button>
            </div>
          ) : state === "complete" ? (
            <div>
              <MediaPlayer
                streamUrl={reel.stream_url}
                playerUrl={reel.player_url}
                title="Strata evidence reel"
              />
              <div className="mt-3 flex items-center justify-between text-[11px] text-white/35">
                <span>{reel.event_ids.length} source moments</span>
                {reel.duration_seconds !== null ? (
                  <span className="tabular-nums">
                    {formatTime(reel.duration_seconds)}
                  </span>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="player-empty aspect-video">
              <span className="player-empty-icon">
                <Icon name="play" className="size-5" />
              </span>
              <p className="mt-4 text-sm text-white/50">
                Your compiled evidence reel will appear here.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
