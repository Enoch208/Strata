import type {
  Archive,
  ChallengeResult,
  Health,
  Investigation,
  ReelRef,
} from "./types";

const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
export const API_BASE_URL = (configuredBase || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(value: unknown, fallback: string): string {
  if (
    typeof value === "object" &&
    value !== null &&
    "detail" in value &&
    typeof value.detail === "object" &&
    value.detail !== null &&
    "message" in value.detail &&
    typeof value.detail.message === "string"
  ) {
    return value.detail.message;
  }
  if (
    typeof value === "object" &&
    value !== null &&
    "detail" in value &&
    typeof value.detail === "string"
  ) {
    return value.detail;
  }
  if (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof value.error === "string"
  ) {
    return value.error;
  }
  return fallback;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Strata could not reach the archive service. Check the API connection and try again.",
    );
  }

  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      errorMessage(data, `The archive service returned ${response.status}.`),
      response.status,
    );
  }
  return data as T;
}

export function getHealth(): Promise<Health> {
  return requestJson("/api/health");
}

export function getArchive(): Promise<Archive> {
  return requestJson("/api/archive");
}

export function createInvestigation(
  query: string,
  archiveId: string,
): Promise<Investigation> {
  return requestJson("/api/investigations", {
    method: "POST",
    body: JSON.stringify({ query, archive_id: archiveId }),
  });
}

export function getInvestigation(id: string): Promise<Investigation> {
  return requestJson(`/api/investigations/${encodeURIComponent(id)}`);
}

export function challengeInvestigation(id: string): Promise<ChallengeResult> {
  return requestJson(`/api/investigations/${encodeURIComponent(id)}/challenge`, {
    method: "POST",
    body: JSON.stringify({ instruction: "Challenge this conclusion" }),
  });
}

export function generateReel(
  id: string,
  eventIds: string[],
): Promise<ReelRef> {
  return requestJson(`/api/investigations/${encodeURIComponent(id)}/reel`, {
    method: "POST",
    body: JSON.stringify({ event_ids: eventIds }),
  });
}

export function packetUrl(id: string): string {
  return `${API_BASE_URL}/api/investigations/${encodeURIComponent(id)}/packet`;
}
