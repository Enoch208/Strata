import type {
  ChallengeResult,
  ClaimEvent,
  Finding,
  Shot,
  SourcedSentence,
} from "@/lib/types";
import { formatDate, formatWindow, outcomeTone, words } from "@/lib/format";
import { Icon } from "./icon";

type Props = {
  challenge: ChallengeResult | null;
  busy: boolean;
  sentences: SourcedSentence[];
  findings: Finding[];
  events: ClaimEvent[];
  shots: Shot[];
  error: string | null;
  onRetry: () => void;
};

export function ChallengePanel({
  challenge,
  busy,
  sentences,
  findings,
  events,
  shots,
  error,
  onRetry,
}: Props) {
  if (!busy && !challenge && !error) return null;

  if (busy) {
    return (
      <section className="challenge-panel animate-scale-in">
        <div className="flex items-center gap-4">
          <span className="processing-mark">
            <Icon name="spark" className="size-5" />
          </span>
          <div>
            <p className="text-sm font-medium text-white">
              Challenging the conclusion
            </p>
            <p className="mt-1 text-xs text-white/40">
              Running a separate archive-wide search with preference for unused
              sources and alternative context.
            </p>
          </div>
        </div>
        <div className="mt-5 h-1 overflow-hidden rounded-full bg-white/5">
          <div className="indeterminate-bar" />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="challenge-panel tone-amber animate-scale-in">
        <p className="text-sm font-medium text-amber-100">Challenge search failed</p>
        <p className="mt-2 text-xs leading-5 text-white/45">{error}</p>
        <button onClick={onRetry} className="secondary-button secondary-button-compact mt-4">
          <Icon name="refresh" />
          Retry challenge
        </button>
      </section>
    );
  }

  if (!challenge) return null;
  const impact = sentences.filter(
    (sentence) =>
      challenge.impact_summary_sentence_ids.includes(sentence.sentence_id) &&
      sentence.support_status === "supported",
  );
  const accepted = findings.filter((finding) =>
    challenge.accepted_finding_ids.includes(finding.finding_id),
  );
  const initial = new Set(challenge.initial_accepted_video_ids);
  const overlap = challenge.challenge_accepted_video_ids.filter((id) =>
    initial.has(id),
  ).length;
  const novelShots = shots.filter((shot) =>
    challenge.novel_accepted_video_ids.includes(shot.video_id),
  );

  return (
    <section className="challenge-panel animate-scale-in">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="eyebrow">
            <span className="tabular-nums text-white/80">03</span>
            <span className="eyebrow-rule" />
            <span>Counter-evidence pass</span>
          </p>
          <h2 className="mt-3 text-2xl font-light tracking-tight text-white">
            Challenge complete
          </h2>
        </div>
        <span className={`outcome-badge ${outcomeTone[challenge.outcome]}`}>
          <span className="status-dot" />
          {words(challenge.outcome)}
        </span>
      </div>

      {!challenge.found_counter_evidence ? (
        <p className="mt-6 rounded-xl border border-white/10 bg-black/20 p-4 text-sm leading-6 text-white/65">
          No counter-evidence was found in this archive. This does not prove the
          conclusion is true.
        </p>
      ) : (
        <>
          <div className="mt-6 space-y-3">
            {impact.map((sentence) => (
              <p
                key={sentence.sentence_id}
                className="border-l border-blue-400/50 pl-4 text-sm leading-6 text-white/70"
              >
                {sentence.text}
              </p>
            ))}
            {accepted.map((finding) => (
              <div key={finding.finding_id} className="detail-card">
                <p className="text-sm font-medium text-white/85">{finding.title}</p>
                <p className="mt-1 text-xs leading-5 text-white/45">
                  {finding.summary}
                </p>
              </div>
            ))}
          </div>

          <div className="novel-source-card">
            <div className="flex items-center gap-3">
              <span className="grid size-9 place-items-center rounded-xl bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-300/20">
                <Icon name="archive" className="size-4" />
              </span>
              <div>
                <p className="text-sm font-medium text-white">
                  {challenge.novel_accepted_video_ids.length} new source
                  {challenge.novel_accepted_video_ids.length === 1 ? "" : "s"} discovered
                </p>
                <p className="mt-1 text-xs text-white/40">
                  The challenge accepted footage absent from the first pass.
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {challenge.novel_accepted_video_ids.map((id) => (
                <code key={id} className="source-id-chip">
                  {id}
                </code>
              ))}
            </div>
            {novelShots.map((shot) => (
              <NovelSourceLink
                key={shot.event_id}
                shot={shot}
                event={events.find((event) => event.event_id === shot.event_id)}
              />
            ))}
          </div>
        </>
      )}

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <AuditMetric
          label="Initial sources"
          value={`${challenge.initial_accepted_video_ids.length} video${challenge.initial_accepted_video_ids.length === 1 ? "" : "s"}`}
        />
        <AuditMetric
          label="Challenge sources"
          value={`${challenge.novel_accepted_video_ids.length} new video${challenge.novel_accepted_video_ids.length === 1 ? "" : "s"}`}
        />
        <AuditMetric label="Source overlap" value={String(overlap)} />
      </div>

      <div className="audit-details mt-5 rounded-xl border border-white/10 bg-black/15 p-4">
        <p className="text-xs font-medium text-white/70">Challenge retrieval audit</p>
        <div className="mt-4 grid gap-5 lg:grid-cols-2">
          <QuerySet title="Initial search queries" queries={challenge.initial_queries} />
          <QuerySet title="Challenge counter-queries" queries={challenge.counter_queries} />
          <SourceSet
            title="Initial accepted video IDs"
            ids={challenge.initial_accepted_video_ids}
          />
          <SourceSet
            title="Challenge accepted video IDs"
            ids={challenge.challenge_accepted_video_ids}
          />
          <div className="lg:col-span-2">
            <p className="detail-label">Rejected challenge candidates</p>
            {challenge.rejected_candidates.length ? (
              <div className="mt-2 space-y-2">
                {challenge.rejected_candidates.map((candidate, index) => (
                  <div
                    key={`${candidate.event_id}-${index}`}
                    className="grid gap-1 rounded-lg border border-white/5 bg-white/[0.02] p-2 text-[10px] sm:grid-cols-[minmax(120px,.35fr)_1fr]"
                  >
                    <code className="break-all text-white/45">{candidate.event_id}</code>
                    <span className="text-white/35">{candidate.reason}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-[10px] text-white/35">
                No rejected candidates in this pass.
              </p>
            )}
          </div>
        </div>
        <p className="mt-4 text-[10px] text-white/30">
          Searched {formatDate(challenge.searched_at.slice(0, 10))}
        </p>
      </div>
    </section>
  );
}

function NovelSourceLink({
  shot,
  event,
}: {
  shot: Shot;
  event: ClaimEvent | undefined;
}) {
  return (
    <a
      href={shot.player_url ?? shot.stream_url ?? shot.source_url}
      target="_blank"
      rel="noreferrer"
      className="mt-3 flex items-center justify-between rounded-lg border border-emerald-300/15 bg-black/20 px-3 py-2 text-[10px] text-emerald-100/70"
    >
      <span>
        {formatDate(shot.source_date)} · {shot.video_title}
      </span>
      <strong>
        Exact evidence {formatWindow(event?.start ?? shot.start, event?.end ?? shot.end)}
      </strong>
    </a>
  );
}

function SourceSet({ title, ids }: { title: string; ids: string[] }) {
  return (
    <div>
      <p className="detail-label">{title}</p>
      <div className="mt-2 space-y-2">
        {ids.map((id) => (
          <code key={id} className="block break-all text-[10px] text-white/45">
            {id}
          </code>
        ))}
      </div>
    </div>
  );
}

function QuerySet({ title, queries }: { title: string; queries: string[] }) {
  return (
    <div>
      <p className="detail-label">{title}</p>
      <ol className="mt-2 space-y-2 text-[10px] leading-5 text-white/45">
        {queries.map((query, index) => (
          <li key={`${query}-${index}`}>
            <span className="mr-2 text-white/20">{index + 1}.</span>
            {query}
          </li>
        ))}
      </ol>
    </div>
  );
}

function AuditMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.025] p-3">
      <p className="detail-label">{label}</p>
      <strong className="mt-2 block text-lg font-light text-white/85">{value}</strong>
    </div>
  );
}
