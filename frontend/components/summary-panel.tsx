import type { SourcedSentence } from "@/lib/types";
import { uniqueVideoCount } from "@/lib/format";
import type { Shot } from "@/lib/types";
import { PrimaryButton } from "./button";
import { Icon } from "./icon";

type Props = {
  sentences: SourcedSentence[];
  shots: Shot[];
  activeSentenceId: string | null;
  challengeBusy: boolean;
  challengeComplete: boolean;
  onSentenceFocus: (sentence: SourcedSentence | null) => void;
  onChallenge: () => void;
};

export function SummaryPanel({
  sentences,
  shots,
  activeSentenceId,
  challengeBusy,
  challengeComplete,
  onSentenceFocus,
  onChallenge,
}: Props) {
  const supported = sentences.filter(
    (sentence) => sentence.support_status === "supported",
  );
  const notEstablished = sentences.filter(
    (sentence) => sentence.support_status === "not_established",
  );
  const partialCount = sentences.filter(
    (sentence) => sentence.support_status === "partially_supported",
  ).length;

  return (
    <section id="evidence-policy" className="summary-panel">
      <div className="flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <p className="eyebrow">
            <span className="tabular-nums text-white/80">02</span>
            <span className="eyebrow-rule" />
            <span>Source-locked conclusion</span>
          </p>
          <h2 className="mt-4 text-3xl font-light tracking-[-0.035em] text-white sm:text-4xl">
            What the archive establishes
          </h2>
          <p className="mt-3 text-xs text-white/35">
            Select a sentence to reveal and highlight its exact supporting events.
          </p>
        </div>

        <PrimaryButton
          onClick={onChallenge}
          disabled={challengeBusy || challengeComplete}
        >
          <Icon name="spark" />
          {challengeBusy
            ? "Challenging…"
            : challengeComplete
              ? "Challenge complete"
              : "Challenge this conclusion"}
        </PrimaryButton>
      </div>

      <div className="mt-8 space-y-3">
        {supported.map((sentence, index) => (
          <button
            key={sentence.sentence_id}
            onClick={() =>
              onSentenceFocus(
                activeSentenceId === sentence.sentence_id ? null : sentence,
              )
            }
            onMouseEnter={() => onSentenceFocus(sentence)}
            onFocus={() => onSentenceFocus(sentence)}
            className={`summary-sentence ${
              activeSentenceId === sentence.sentence_id ? "summary-sentence-active" : ""
            }`}
            aria-pressed={activeSentenceId === sentence.sentence_id}
          >
            <span className="summary-number tabular-nums">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="flex-1">{sentence.text}</span>
            <span className="citation-count">
              {sentence.supported_by_event_ids.length}{" "}
              {sentence.supported_by_event_ids.length === 1 ? "source" : "sources"}
              <Icon name="inspect" className="size-3.5" />
            </span>
          </button>
        ))}

        {notEstablished.map((sentence) => (
          <div key={sentence.sentence_id} className="uncertainty-row">
            <Icon name="shield" className="size-4 shrink-0" />
            <span>Not established by this archive.</span>
          </div>
        ))}

        {partialCount > 0 ? (
          <div className="uncertainty-row">
            <Icon name="inspect" className="size-4 shrink-0" />
            <span>
              Partial evidence / needs review — {partialCount} unsupported{" "}
              {partialCount === 1 ? "sentence was" : "sentences were"} withheld.
            </span>
          </div>
        ) : null}
      </div>

      <p className="mt-6 text-xs text-white/40">
        Based on {shots.length} moments across {uniqueVideoCount(shots)} source
        videos.
      </p>
    </section>
  );
}
