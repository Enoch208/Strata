import type { ClaimEvent, Shot } from "@/lib/types";
import { formatDate, formatWindow, words } from "@/lib/format";
import { Icon } from "./icon";

export function SourceDetails({
  event,
  shot,
}: {
  event: ClaimEvent | null;
  shot: Shot | null;
}) {
  return (
    <aside className="flex h-full min-h-[520px] flex-col bg-black/30">
      <div className="panel-toolbar">
        <span>Source details</span>
        <Icon name="inspect" className="size-3.5 text-white/30" />
      </div>
      {!event ? (
        <div className="grid flex-1 place-items-center p-6 text-center text-xs text-white/35">
          Indexed fields and transcript will appear here.
        </div>
      ) : (
        <div className="flex-1 space-y-3 overflow-y-auto p-3">
          <div className="detail-card">
            <p className="detail-label">Video</p>
            <p className="mt-2 text-xs leading-5 text-white/70">
              {shot?.video_title ?? event.video_id}
            </p>
            <div className="mt-3 space-y-1.5 text-[10px] text-white/35">
              <p>{event.source_organization}</p>
              <p>{formatDate(event.source_date)}</p>
              <p className="tabular-nums">
                {formatWindow(event.start, event.end)}
              </p>
              <code className="block break-all pt-1 text-white/25">
                {event.video_id}
              </code>
            </div>
            {shot?.source_url ? (
              <a
                href={shot.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-1 text-[10px] text-blue-300"
              >
                Original source <Icon name="arrow" className="size-3" />
              </a>
            ) : null}
          </div>

          <div className="detail-card">
            <p className="detail-label">Transcript at source</p>
            <blockquote className="mt-3 border-l border-blue-400/40 pl-3 text-xs font-light leading-5 text-white/60">
              {shot?.transcript_text ||
                "No transcript text was returned for this window."}
            </blockquote>
          </div>

          <div className="detail-card">
            <p className="detail-label">Indexed fields</p>
            <dl className="mt-3 space-y-2 text-[10px]">
              <Detail label="Claim type" value={words(event.claim_type)} />
              <Detail label="Status" value={words(event.status)} />
              <Detail label="Certainty" value={words(event.certainty)} />
              <Detail
                label="Speaker"
                value={event.speaker_name ?? event.speaker_role ?? "Not identified"}
              />
              {event.normalized_value ? (
                <Detail label="Normalized" value={event.normalized_value} />
              ) : null}
            </dl>
          </div>

          {event.reason ? (
            <div className="detail-card">
              <p className="detail-label">Evidence reason</p>
              <p className="mt-2 text-xs leading-5 text-white/50">{event.reason}</p>
            </div>
          ) : null}
        </div>
      )}
    </aside>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-white/30">{label}</dt>
      <dd className="text-right text-white/60">{value}</dd>
    </div>
  );
}
