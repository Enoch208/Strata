"use client";

import { useState } from "react";
import {
  challengeInvestigation,
  createInvestigation,
  generateReel,
  getInvestigation,
} from "@/lib/api";
import type {
  Archive,
  Investigation,
  InvestigationState,
  ReelState,
} from "@/lib/types";

const TERMINAL_STATES: InvestigationState[] = [
  "complete",
  "insufficient_evidence",
  "failed",
];

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export function useInvestigation() {
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState<string | null>(null);
  const [progress, setProgress] = useState<InvestigationState | null>(null);
  const [challengeBusy, setChallengeBusy] = useState(false);
  const [challengeError, setChallengeError] = useState<string | null>(null);
  const [reelState, setReelState] = useState<ReelState>("idle");
  const [reelError, setReelError] = useState<string | null>(null);

  async function pollUntilTerminal(initial: Investigation) {
    let current = initial;
    while (!TERMINAL_STATES.includes(current.state)) {
      setInvestigation(current);
      setProgress(current.state);
      await wait(1200);
      current = await getInvestigation(current.investigation_id);
    }
    return current;
  }

  async function investigate(archive: Archive, query: string) {
    setLastQuery(query);
    setInvestigation(null);
    setFailure(null);
    setProgress("searching");
    setChallengeError(null);
    setReelError(null);
    setReelState("idle");
    try {
      const created = await createInvestigation(query, archive.archive_id);
      const completed = await pollUntilTerminal(created);
      setInvestigation(completed);
      setProgress(null);
      if (completed.reel.stream_url) setReelState("complete");
      else if (completed.reel.error) setReelState("failed");
    } catch (caught) {
      setProgress(null);
      setFailure(
        caught instanceof Error ? caught.message : "Investigation failed.",
      );
    }
  }

  async function runChallenge() {
    if (!investigation?.investigation_id) return;
    setChallengeBusy(true);
    setChallengeError(null);
    try {
      const challenge = await challengeInvestigation(
        investigation.investigation_id,
      );
      try {
        const refreshed = await getInvestigation(
          investigation.investigation_id,
        );
        setInvestigation(refreshed);
      } catch {
        setInvestigation((current) =>
          current ? { ...current, challenge } : current,
        );
      }
    } catch (caught) {
      setChallengeError(
        caught instanceof Error ? caught.message : "Challenge search failed.",
      );
    } finally {
      setChallengeBusy(false);
    }
  }

  async function runReel(eventIds: string[]) {
    if (!investigation?.investigation_id || eventIds.length === 0) return;
    setReelState("generating");
    setReelError(null);
    try {
      const reel = await generateReel(investigation.investigation_id, eventIds);
      setInvestigation((current) => (current ? { ...current, reel } : current));
      if (reel.stream_url && !reel.error) {
        setReelState("complete");
      } else {
        setReelState("failed");
        setReelError(reel.error);
      }
    } catch (caught) {
      setReelState("failed");
      setReelError(
        caught instanceof Error ? caught.message : "Reel generation failed.",
      );
    }
  }

  return {
    investigation,
    failure,
    lastQuery,
    progress,
    challengeBusy,
    challengeError,
    reelState,
    reelError,
    investigate,
    runChallenge,
    runReel,
  };
}
