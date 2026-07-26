import type { Investigation, SourcedSentence } from "@/lib/types";
import { formatWindow, labelTone, words } from "@/lib/format";
import { Icon } from "./icon";

type Props = {
  investigation: Investigation;
  activeSentenceId: string | null;
  onSentenceSelect: (sentence: SourcedSentence) => void;
};

export function EvidenceInspector({
  investigation,
  activeSentenceId,
  onSentenceSelect,
}: Props) {
  return (
    <details className="inspector-shell animate-on-scroll" open>
      <summary className="inspector-summary">
        <span className="flex items-center gap-2">
          <Icon name="inspect" className="size-4 text-blue-300" />
          Evidence inspector
        </span>
        <span className="text-[11px] font-normal text-white/35">
          Sentence map · relations · audit trace
        </span>
      </summary>

      <div className="grid border-t border-white/10 lg:grid-cols-3">
        <section className="inspector-column">
          <p className="detail-label">Sentence → event map</p>
          <div className="mt-4 space-y-2">
            {investigation.summary_sentences.map((sentence) =>
              sentence.support_status === "supported" ? (
                <button
                  key={sentence.sentence_id}
                  onClick={() => onSentenceSelect(sentence)}
                  className={`inspector-row ${
                    activeSentenceId === sentence.sentence_id
                      ? "inspector-row-active"
                      : ""
                  }`}
                >
                  <span className="line-clamp-2">{sentence.text}</span>
                  <span className="mt-2 flex flex-wrap gap-1.5">
                    {sentence.supported_by_event_ids.map((id) => (
                      <code key={id} className="event-id-chip">
                        {id}
                      </code>
                    ))}
                  </span>
                </button>
              ) : (
                <div key={sentence.sentence_id} className="inspector-row">
                  <span className="text-amber-200/60">
                    {sentence.support_status === "not_established"
                      ? "Not established by this archive."
                      : "Partially supported sentence withheld."}
                  </span>
                </div>
              ),
            )}
          </div>
        </section>

        <section className="inspector-column border-white/10 lg:border-x">
          <p className="detail-label">Claim relations</p>
          <div className="mt-4 space-y-2">
            {investigation.relations.length ? (
              investigation.relations.map((relation) => (
                <div key={relation.relation_id} className="inspector-row">
                  <div className="flex items-center justify-between gap-2">
                    <span className="finding-badge tone-neutral">
                      {words(relation.relation_type)}
                    </span>
                    <span className="text-[10px] text-white/30">
                      {words(relation.confidence)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-white/50">
                    {relation.explanation}
                  </p>
                  <p className="mt-2 font-mono text-[9px] text-white/25">
                    {relation.from_event_id} → {relation.to_event_id}
                  </p>
                </div>
              ))
            ) : (
              <p className="inspector-empty">No claim relations were returned.</p>
            )}
          </div>
        </section>

        <section className="inspector-column">
          <p className="detail-label">Challenge audit</p>
          <div className="mt-4 space-y-2">
            {investigation.challenge ? (
              <>
                {investigation.challenge.rejected_candidates.map((candidate) => (
                  <div key={candidate.event_id} className="inspector-row">
                    <span className="finding-badge tone-amber">
                      Rejected candidate
                    </span>
                    <p className="mt-2 font-mono text-[10px] text-white/40">
                      {candidate.event_id}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-white/45">
                      {candidate.reason}
                    </p>
                  </div>
                ))}
                {investigation.challenge.rejected_candidates.length === 0 ? (
                  <p className="inspector-empty">
                    No rejected challenge candidates were returned.
                  </p>
                ) : null}
              </>
            ) : (
              <p className="inspector-empty">
                Run the challenge pass to inspect candidate decisions.
              </p>
            )}
          </div>
        </section>
      </div>

      <div className="border-t border-white/10 p-4">
        <p className="detail-label">Accepted event index</p>
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {investigation.events.map((event) => {
            const finding = investigation.findings.find((item) =>
              item.event_ids.includes(event.event_id),
            );
            return (
              <a
                key={event.event_id}
                href={`#event-${event.event_id}`}
                className="event-index-card"
              >
                <span
                  className={`finding-badge ${
                    finding ? labelTone[finding.label] : "tone-neutral"
                  }`}
                >
                  {words(finding?.label ?? event.claim_type)}
                </span>
                <code className="mt-2 block text-[10px] text-white/35">
                  {event.event_id}
                </code>
                <span className="mt-1 block tabular-nums text-[10px] text-white/25">
                  {formatWindow(event.start, event.end)}
                </span>
              </a>
            );
          })}
        </div>
      </div>
    </details>
  );
}
