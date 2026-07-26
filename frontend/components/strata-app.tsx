"use client";

import type { Archive, InvestigationState } from "@/lib/types";
import { formatDate, progressCopy } from "@/lib/format";
import { Icon } from "./icon";
import { useInvestigateContext } from "./investigate-context";
import { InvestigationWorkspace } from "./investigation-workspace";
import { isProgressState } from "./investigation-progress";
import { QueryComposer } from "./query-composer";
import { StatePanel } from "./state-panel";

const progressStages = ["searching", "retrieving", "comparing", "building"] as const;

export function StrataApp() {
  const { archiveState, work, canInvestigate, investigate } =
    useInvestigateContext();
  const hasCompletedInvestigation = work.investigation?.state === "complete";

  return (
    <div
      className={
        hasCompletedInvestigation ? "investigate-result-mode min-h-full" : ""
      }
    >
      {!hasCompletedInvestigation ? (
        <DashboardHome
          archive={archiveState.archive}
          error={archiveState.error}
          ready={canInvestigate}
          busy={isProgressState(work.progress)}
          onInvestigate={investigate}
        />
      ) : null}

      {isProgressState(work.progress) ? (
        <DashboardProgress state={work.progress} />
      ) : null}

      {work.investigation?.state === "complete" ? (
        <div id="evidence" className="py-6">
          <InvestigationWorkspace
            key={work.investigation.investigation_id}
            investigation={work.investigation}
            challengeBusy={work.challengeBusy}
            challengeError={work.challengeError}
            reelState={work.reelState}
            reelError={work.reelError}
            onChallenge={() => void work.runChallenge()}
            onGenerateReel={(ids) => void work.runReel(ids)}
          />
        </div>
      ) : null}

      {work.investigation?.state === "insufficient_evidence" ? (
        <div className="investigate-dark-state">
          <StatePanel
            kind="insufficient"
            title="The archive does not contain enough evidence to make this comparison."
            detail={work.investigation.insufficient_evidence_reason}
            onRetry={() => document.getElementById("archive-query")?.focus()}
          />
        </div>
      ) : null}

      {work.investigation?.state === "failed" || work.failure ? (
        <div className="investigate-dark-state">
          <StatePanel
            kind="failed"
            title="The investigation could not be completed."
            detail={work.investigation?.error ?? work.failure}
            onRetry={() => {
              if (archiveState.archive && work.lastQuery) {
                void work.investigate(archiveState.archive, work.lastQuery);
              }
            }}
          />
        </div>
      ) : null}
    </div>
  );
}

function DashboardHome({
  archive,
  error,
  ready,
  busy,
  onInvestigate,
}: {
  archive: Archive | null;
  error: string | null;
  ready: boolean;
  busy: boolean;
  onInvestigate: (query: string) => void;
}) {
  const videos = archive?.videos.slice(0, 4) ?? [];
  const primarySource =
    archive?.videos.find((video) => video.index_status === "ready") ??
    archive?.videos[0] ??
    null;
  const claimEvents = archive?.stats.claim_event_count ?? 0;
  const statusChanges = archive?.stats.status_change_count ?? 0;
  const videoCount = archive?.stats.video_count ?? 0;

  return (
    <main id="new-investigation" className="investigate-home">
      <div className="investigate-content-grid">
        <section className="investigate-primary-column">
          <div className="investigate-intro">
            <div>
              <span className="investigate-kicker">
                <Icon name="spark" />
                New investigation
              </span>
              <h1>Ask the archive what changed.</h1>
              <p>
                Search every source, compare claims over time, and keep each
                conclusion attached to the exact footage.
              </p>
            </div>
            <span className="investigate-case-number">CASE / 001</span>
          </div>

          <QueryComposer
            disabled={!ready}
            busy={busy}
            onSubmit={onInvestigate}
          />

          <section id="evidence-viewer" className="investigate-evidence-viewer">
            <div className="investigate-evidence-overlay" />
            <div className="investigate-viewer-topline">
              <span>
                <i />
                Source-ready workspace
              </span>
              <span>{videoCount || "—"} indexed sources</span>
            </div>
            <div className="investigate-viewer-copy">
              {primarySource ? (
                <a
                  href={primarySource.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="investigate-play-mark"
                  aria-label={`Open ${primarySource.title}`}
                >
                  <Icon name="play" />
                </a>
              ) : (
                <a
                  href="#archive-query"
                  className="investigate-play-mark"
                  aria-label="Focus the archive query"
                >
                  <Icon name="search" />
                </a>
              )}
              <div>
                <p>Evidence player</p>
                <h2>Every answer opens on the exact source moment.</h2>
              </div>
            </div>
            <div className="investigate-viewer-footer">
              <span>Official archive source</span>
              <div>
                <i />
                <i />
                <i />
                <i />
              </div>
              <span>Timestamp locked</span>
            </div>
          </section>

          <div className="investigate-activity-strip">
            <span className="investigate-waveform" aria-hidden="true">
              {Array.from({ length: 18 }).map((_, index) => (
                <i key={index} />
              ))}
            </span>
            <div>
              <small>Archive intelligence</small>
              <p>
                Ask a temporal question above. Strata will retrieve, compare,
                challenge, and compile the evidence.
              </p>
            </div>
          </div>

          <div className="investigate-analysis-grid">
            <article id="evidence-reels" className="investigate-analysis-card">
              <div className="investigate-card-heading">
                <div>
                  <p>Archive coverage</p>
                  <span>Indexed source material</span>
                </div>
                <Icon name="archive" />
              </div>
              <div className="investigate-coverage-facts">
                <CoverageFact label="Source videos" value={videoCount} />
                <CoverageFact label="Claim events" value={claimEvents} />
                <CoverageFact label="Status changes" value={statusChanges} />
              </div>
            </article>

            <article className="investigate-analysis-card">
              <div className="investigate-card-heading">
                <div>
                  <p>Evidence reel path</p>
                  <span>Four source-locked passes</span>
                </div>
                <Icon name="shield" />
              </div>
              <div className="investigate-protocol">
                {[
                  ["01", "Search"],
                  ["02", "Retrieve"],
                  ["03", "Compare"],
                  ["04", "Challenge"],
                ].map(([number, label]) => (
                  <div key={number}>
                    <span>{number}</span>
                    <p>{label}</p>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>

        <aside className="investigate-intelligence-column">
          <section className="investigate-metric-card">
            <div className="investigate-side-heading">
              <div>
                <p>Archive signal</p>
                <span>Live index overview</span>
              </div>
              <a href="#source-intelligence" aria-label="View archive sources">
                <Icon name="inspect" />
              </a>
            </div>
            <div className="investigate-metric-grid">
              <SignalMetric value={videoCount} label="Indexed sources" />
              <SignalMetric value={claimEvents} label="Claim events" />
            </div>
          </section>

          <section
            id="source-intelligence"
            className="investigate-sources-card"
          >
            <div className="investigate-side-heading">
              <div>
                <p>Source intelligence</p>
                <span>Recent archive material</span>
              </div>
              <span className="investigate-source-count">{videoCount || "—"}</span>
            </div>
            <div className="investigate-source-list">
              {videos.length ? (
                videos.map((video, index) => (
                  <a
                    key={video.video_id}
                    href={video.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span className="investigate-source-index">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <p>{video.title}</p>
                      <span>
                        {video.source_organization} ·{" "}
                        {formatDate(video.source_date)}
                      </span>
                    </div>
                    <i className={video.index_status === "ready" ? "is-ready" : ""} />
                  </a>
                ))
              ) : (
                <div className="investigate-source-empty">
                  <Icon name={error ? "x" : "archive"} />
                  <p>{error ?? "Reading the archive manifest…"}</p>
                </div>
              )}
            </div>
          </section>

          <section id="evidence-policy" className="investigate-policy-card">
            <span>
              <Icon name="shield" />
            </span>
            <div>
              <p>Evidence policy</p>
              <strong>If the archive cannot establish it, Strata says so.</strong>
              <small>Exact timestamps · sentence mapping · challenge pass</small>
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}

function CoverageFact({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="investigate-coverage-fact">
      <span>{label}</span>
      <strong>{value || "—"}</strong>
    </div>
  );
}

function SignalMetric({
  value,
  label,
}: {
  value: number;
  label: string;
}) {
  return (
    <div className="investigate-signal-metric">
      <strong>{value || "—"}</strong>
      <span>{label}</span>
    </div>
  );
}

function DashboardProgress({
  state,
}: {
  state: Exclude<
    InvestigationState,
    "complete" | "insufficient_evidence" | "failed"
  >;
}) {
  const activeIndex = progressStages.indexOf(state);

  return (
    <section className="investigate-progress">
      <div>
        <span className="investigate-progress-icon">
          <Icon name="spark" />
        </span>
        <div>
          <small>Investigation running</small>
          <p>{progressCopy[state]}</p>
        </div>
      </div>
      <div className="investigate-progress-stages">
        {progressStages.map((stage, index) => (
          <span
            key={stage}
            className={
              index < activeIndex
                ? "is-complete"
                : index === activeIndex
                  ? "is-active"
                  : ""
            }
          >
            {index < activeIndex ? <Icon name="check" /> : `0${index + 1}`}
            {stage}
          </span>
        ))}
      </div>
    </section>
  );
}
