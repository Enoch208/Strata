import type {
  Archive,
  Investigation,
  SubmissionProof,
} from "@/lib/types";
import { Icon } from "./icon";

type Props = {
  archive: Archive | null;
  proof: SubmissionProof | null;
  investigation?: Investigation;
};

export function SubmissionProofPanel({
  archive,
  proof,
  investigation,
}: Props) {
  if (!proof) return null;

  const displayable =
    investigation?.summary_sentences.filter(
      (sentence) => sentence.support_status === "supported",
    ) ?? [];
  const sourceLocked = displayable.filter(
    (sentence) => sentence.supported_by_event_ids.length > 0,
  ).length;
  const invalidLinks =
    investigation?.shots.filter(
      (shot) => !shot.stream_url || shot.end <= shot.start,
    ).length ?? null;
  const novelty = investigation?.challenge
    ? investigation.challenge.novel_accepted_video_ids.length > 0
    : null;
  const indexChecks = Object.values(proof.index_proof);

  return (
    <section className="glass-panel submission-proof-panel animate-on-scroll">
      <div className="flex flex-col gap-4 border-b border-white/10 p-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">
            <Icon name="shield" className="size-4 text-emerald-300" />
            <span>Integrity + frozen evaluation</span>
          </p>
          <h2 className="mt-3 text-xl font-light text-white">
            Proof, not presentation claims.
          </h2>
        </div>
        <span className="text-[10px] text-white/35">
          {proof.evaluation_cases} frozen questions · raw counts shown
        </span>
      </div>

      <div className="grid lg:grid-cols-[1.05fr_.95fr]">
        <div className="border-b border-white/10 p-5 lg:border-b-0 lg:border-r">
          <p className="detail-label">Comparative result</p>
          <div className="mt-4 overflow-hidden rounded-xl border border-white/10">
            <div className="proof-table-row proof-table-head">
              <span>System</span>
              <span>Retrieval recall</span>
              <span>Unsupported claims</span>
            </div>
            {proof.evaluation.map((arm) => (
              <div className="proof-table-row" key={arm.arm}>
                <strong>{arm.label}</strong>
                <span>
                  {arm.retrieval_recall.numerator}/
                  {arm.retrieval_recall.denominator}
                  <small>{formatPercent(arm.retrieval_recall.percentage)}</small>
                </span>
                <span>
                  {arm.unsupported_claims.numerator}/
                  {arm.unsupported_claims.denominator}
                  <small>{formatPercent(arm.unsupported_claims.percentage)}</small>
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[10px] leading-5 text-white/35">
            Strata adds playable citations, temporal comparison, a separate
            challenge retrieval pass, and sentence-level source locking.
          </p>
        </div>

        <div className="p-5">
          <p className="detail-label">Machine-derived integrity</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            <ProofCheck
              label="Distinct VideoDB IDs"
              value={`${proof.distinct_video_ids}/6`}
              passed={proof.distinct_video_ids === 6}
            />
            <ProofCheck
              label="Speech · OCR · visual"
              value={`${indexChecks.slice(0, 3).filter(Boolean).length}/3 ready`}
              passed={indexChecks.slice(0, 3).every(Boolean)}
            />
            <ProofCheck
              label="Claim + finding indexes"
              value={`${indexChecks.slice(3).filter(Boolean).length}/2 ready`}
              passed={indexChecks.slice(3).every(Boolean)}
            />
            <ProofCheck
              label="Live aggregate()"
              value={
                archive
                  ? `${archive.stats.claim_event_count} events · ${archive.stats.video_count} videos`
                  : "Awaiting archive"
              }
              passed={Boolean(archive)}
            />
            <ProofCheck
              label="Sentence source locks"
              value={
                investigation
                  ? `${sourceLocked}/${displayable.length} (${displayable.length ? Math.round((sourceLocked / displayable.length) * 100) : 0}%)`
                  : "Measured after run"
              }
              passed={
                investigation ? sourceLocked === displayable.length : null
              }
            />
            <ProofCheck
              label="Invalid evidence links"
              value={invalidLinks === null ? "Measured after run" : String(invalidLinks)}
              passed={invalidLinks === null ? null : invalidLinks === 0}
            />
            <ProofCheck
              label="Challenge novelty"
              value={
                novelty === null
                  ? "Measured after challenge"
                  : novelty
                    ? "Passed"
                    : "No new source"
              }
              passed={novelty}
            />
            <ProofCheck
              label="Repository tests"
              value={
                proof.verification.tests_passed
                  ? `${proof.verification.tests_passed} passed`
                  : "Verification pending"
              }
              passed={
                proof.verification.tests_passed
                  ? true
                  : null
              }
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function ProofCheck({
  label,
  value,
  passed,
}: {
  label: string;
  value: string;
  passed: boolean | null;
}) {
  return (
    <div className="proof-check">
      <span
        className={
          passed === null
            ? "proof-dot"
            : passed
              ? "proof-dot is-passed"
              : "proof-dot is-failed"
        }
      />
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function formatPercent(value: number | null): string {
  return value === null ? "n/a" : `${value.toFixed(1)}%`;
}
