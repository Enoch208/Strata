"use client";

import { useState } from "react";
import type { Investigation, ReelState, SourcedSentence } from "@/lib/types";
import { eventFor, shotFor } from "@/lib/format";
import { packetUrl } from "@/lib/api";
import { ChallengePanel } from "./challenge-panel";
import { EvidenceInspector } from "./evidence-inspector";
import { EvidencePlayer } from "./evidence-player";
import { EvidenceTimeline } from "./evidence-timeline";
import { Icon } from "./icon";
import { ReelPanel } from "./reel-panel";
import { SourceDetails } from "./source-details";
import { SummaryPanel } from "./summary-panel";

type Props = {
  investigation: Investigation;
  challengeBusy: boolean;
  challengeError: string | null;
  reelState: ReelState;
  reelError: string | null;
  onChallenge: () => void;
  onGenerateReel: (eventIds: string[]) => void;
};

export function InvestigationWorkspace({
  investigation,
  challengeBusy,
  challengeError,
  reelState,
  reelError,
  onChallenge,
  onGenerateReel,
}: Props) {
  const firstEventId =
    investigation.shots.find((shot) => shot.stream_url)?.event_id ??
    investigation.events[0]?.event_id ??
    null;
  const [selectedEventId, setSelectedEventId] = useState<string | null>(
    firstEventId,
  );
  const [activeSentence, setActiveSentence] =
    useState<SourcedSentence | null>(null);
  const [reelEventIds, setReelEventIds] = useState<string[]>(() => {
    if (investigation.reel.event_ids.length) return investigation.reel.event_ids;
    return investigation.shots
      .filter((shot) => shot.stream_url)
      .map((shot) => shot.event_id);
  });

  const selectedEvent = selectedEventId
    ? eventFor(investigation.events, selectedEventId) ?? null
    : null;
  const selectedShot = selectedEventId
    ? shotFor(investigation.shots, selectedEventId) ?? null
    : null;

  function focusSentence(sentence: SourcedSentence | null) {
    setActiveSentence(sentence);
    if (sentence?.supported_by_event_ids[0]) {
      setSelectedEventId(sentence.supported_by_event_ids[0]);
    }
  }

  function toggleReel(eventId: string) {
    setReelEventIds((current) =>
      current.includes(eventId)
        ? current.filter((id) => id !== eventId)
        : [...current, eventId],
    );
  }

  return (
    <main className="mx-auto w-full max-w-[1500px] space-y-6 px-4 pb-20 sm:px-6 lg:px-8">
      <div className="section-heading border-y border-white/10 px-1 py-6">
        <div>
          <p className="eyebrow">
            <span className="status-dot bg-emerald-400" />
            <span>Completed investigation</span>
          </p>
          <h2 className="mt-3 max-w-4xl text-xl font-light tracking-tight text-white sm:text-2xl">
            {investigation.query}
          </h2>
        </div>
        <a
          href={packetUrl(investigation.investigation_id)}
          download
          className="secondary-button"
        >
          <Icon name="download" />
          Evidence packet
        </a>
      </div>

      <SummaryPanel
        sentences={investigation.summary_sentences}
        shots={investigation.shots}
        activeSentenceId={activeSentence?.sentence_id ?? null}
        challengeBusy={challengeBusy}
        challengeComplete={Boolean(investigation.challenge)}
        onSentenceFocus={focusSentence}
        onChallenge={onChallenge}
      />

      <ChallengePanel
        challenge={investigation.challenge}
        busy={challengeBusy}
        sentences={investigation.summary_sentences}
        findings={investigation.findings}
        error={challengeError}
        onRetry={onChallenge}
      />

      <section className="editor-shell animate-on-scroll">
        <div className="editor-topbar">
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-red-500/70" />
            <span className="size-2.5 rounded-full bg-amber-300/70" />
            <span className="size-2.5 rounded-full bg-emerald-400/70" />
          </div>
          <div className="flex items-center gap-2">
            <Icon name="shield" className="size-3 text-emerald-300" />
            <span>Strata evidence workspace</span>
          </div>
        </div>
        <div className="grid lg:grid-cols-12 lg:min-h-[650px] lg:max-h-[760px]">
          <div className="border-b border-white/10 lg:col-span-3 lg:border-b-0 lg:border-r">
            <EvidenceTimeline
              events={investigation.events}
              findings={investigation.findings}
              shots={investigation.shots}
              selectedEventId={selectedEventId}
              highlightedEventIds={
                activeSentence?.supported_by_event_ids ?? []
              }
              reelEventIds={reelEventIds}
              onSelect={setSelectedEventId}
              onToggleReel={toggleReel}
            />
          </div>
          <div className="border-b border-white/10 lg:col-span-6 lg:border-b-0">
            <EvidencePlayer event={selectedEvent} shot={selectedShot} />
          </div>
          <div className="lg:col-span-3 lg:border-l lg:border-white/10">
            <SourceDetails event={selectedEvent} shot={selectedShot} />
          </div>
        </div>
      </section>

      <EvidenceInspector
        investigation={investigation}
        activeSentenceId={activeSentence?.sentence_id ?? null}
        onSentenceSelect={focusSentence}
      />

      <ReelPanel
        events={investigation.events}
        shots={investigation.shots}
        selectedEventIds={reelEventIds}
        reel={investigation.reel}
        state={reelState}
        error={reelError}
        onGenerate={() => onGenerateReel(reelEventIds)}
      />
    </main>
  );
}
