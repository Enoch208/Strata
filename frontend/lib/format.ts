import type {
  ChallengeOutcome,
  ClaimEvent,
  FindingLabel,
  InvestigationState,
  Shot,
} from "./types";

export function words(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatTime(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const remainder = whole % 60;
  const values = hours > 0 ? [hours, minutes, remainder] : [minutes, remainder];
  return values
    .map((value, index) =>
      index === 0 ? String(value) : String(value).padStart(2, "0"),
    )
    .join(":");
}

export function formatWindow(start: number, end: number): string {
  return `${formatTime(start)}–${formatTime(end)}`;
}

export const progressCopy: Record<
  Extract<
    InvestigationState,
    "searching" | "retrieving" | "comparing" | "building"
  >,
  string
> = {
  searching: "Searching the archive",
  retrieving: "Retrieving source moments",
  comparing: "Comparing statements over time",
  building: "Building the evidence trail",
};

export const labelTone: Record<FindingLabel, string> = {
  confirmed_change: "tone-emerald",
  correction: "tone-emerald",
  potential_tension: "tone-red",
  consistent_statement: "tone-neutral",
  new_information: "tone-neutral",
  insufficient_evidence: "tone-amber",
  needs_review: "tone-amber",
};

export const outcomeTone: Record<ChallengeOutcome, string> = {
  unchanged: "tone-neutral",
  qualified: "tone-blue",
  revised: "tone-amber",
};

export function uniqueVideoCount(shots: Shot[]): number {
  return new Set(shots.map((shot) => shot.video_id)).size;
}

export function eventFor(
  events: ClaimEvent[],
  eventId: string,
): ClaimEvent | undefined {
  return events.find((event) => event.event_id === eventId);
}

export function shotFor(
  shots: Shot[],
  eventId: string,
): Shot | undefined {
  return shots.find((shot) => shot.event_id === eventId);
}
