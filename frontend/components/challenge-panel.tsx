import type {
  ChallengeResult,
  Finding,
  SourcedSentence,
} from "@/lib/types";
import { formatDate, outcomeTone, words } from "@/lib/format";
import { Icon } from "./icon";

type Props = {
  challenge: ChallengeResult | null;
  busy: boolean;
  sentences: SourcedSentence[];
  findings: Finding[];
  error: string | null;
  onRetry: () => void;
};

export function ChallengePanel({
  challenge,
  busy,
  sentences,
  findings,
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
                <p className="text-sm font-medium text-white">New source reached</p>
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
          </div>
        </>
      )}

      <details className="audit-details mt-5">
        <summary>Inspect source sets and counter-queries</summary>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <SourceSet title="Initial pass" ids={challenge.initial_accepted_video_ids} />
          <SourceSet
            title="Challenge pass"
            ids={challenge.challenge_accepted_video_ids}
          />
          <div>
            <p className="detail-label">Counter-queries</p>
            <ol className="mt-2 space-y-2 text-xs leading-5 text-white/45">
              {challenge.counter_queries.map((query, index) => (
                <li key={`${query}-${index}`}>{query}</li>
              ))}
            </ol>
          </div>
        </div>
        <p className="mt-4 text-[10px] text-white/30">
          Searched {formatDate(challenge.searched_at.slice(0, 10))}
        </p>
      </details>
    </section>
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
