"use client";

import Link from "next/link";
import { formatDate, formatTime } from "@/lib/format";
import { Icon } from "./icon";
import { useInvestigateContext } from "./investigate-context";
import { InvestigationWorkspace } from "./investigation-workspace";
import { ReelPanel } from "./reel-panel";

type RouteMode = "sources" | "evidence" | "reels" | "policy";

export function InvestigateRoutePage({ mode }: { mode: RouteMode }) {
  if (mode === "sources") return <SourcesRoute />;
  if (mode === "evidence") return <EvidenceRoute />;
  if (mode === "reels") return <ReelsRoute />;
  return <PolicyRoute />;
}

function SourcesRoute() {
  const { archiveState } = useInvestigateContext();
  const { archive, error, loading } = archiveState;

  return (
    <RouteFrame
      eyebrow="Source manifest"
      title="Every source in the investigation archive."
      copy="First-party footage, index status, dates, and source ownership remain visible before any investigation begins."
      action={
        <Link href="/investigate" className="investigate-route-action">
          <Icon name="search" />
          Start investigation
        </Link>
      }
    >
      <div className="investigate-route-stat-grid">
        <RouteStat
          label="Indexed sources"
          value={archive ? String(archive.stats.video_count) : "—"}
          icon="archive"
        />
        <RouteStat
          label="Indexed duration"
          value={archive?.indexed_duration_label ?? "—"}
          icon="film"
        />
        <RouteStat
          label="Manifest state"
          value={archive?.index_status ?? (loading ? "Connecting" : "Offline")}
          icon="check"
        />
      </div>

      <section className="investigate-route-panel">
        <div className="investigate-route-panel-heading">
          <div>
            <p>Archive inventory</p>
            <span>Original source links open in a new tab</span>
          </div>
          <span>{archive?.videos.length ?? 0} sources</span>
        </div>

        <div className="investigate-source-table">
          {archive?.videos.length ? (
            archive.videos.map((video, index) => (
              <a
                key={video.video_id}
                href={video.source_url}
                target="_blank"
                rel="noreferrer"
              >
                <span className="investigate-source-table-index">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="investigate-source-table-main">
                  <strong>{video.title}</strong>
                  <small>
                    {video.source_organization} · {formatDate(video.source_date)}
                  </small>
                </span>
                <span className="investigate-source-table-duration">
                  {formatTime(video.duration_seconds)}
                </span>
                <span
                  className={`investigate-source-table-state ${
                    video.index_status === "ready" ? "is-ready" : ""
                  }`}
                >
                  <i />
                  {video.index_status}
                </span>
                <Icon name="arrow" />
              </a>
            ))
          ) : (
            <RouteEmpty
              icon={error ? "x" : "archive"}
              title={error ? "Archive unavailable" : "Reading source manifest"}
              copy={
                error ??
                "The source inventory will appear as soon as the archive service responds."
              }
            />
          )}
        </div>
      </section>
    </RouteFrame>
  );
}

function EvidenceRoute() {
  const { work } = useInvestigateContext();
  const investigation = work.investigation;

  if (investigation?.state !== "complete") {
    return (
      <RouteFrame
        eyebrow="Evidence workspace"
        title="No completed investigation yet."
        copy="Run an archive question first. Accepted claims, citations, source windows, and the challenge pass will appear here."
      >
        <RouteEmpty
          icon="inspect"
          title="Evidence is created from a real investigation"
          copy="Strata does not prefill this workspace with plausible-looking sample conclusions."
          actionLabel="Start an investigation"
          actionHref="/investigate"
          details={[
            ["Claim map", "Accepted sentence → event IDs"],
            ["Source window", "Video, date, and exact timestamp"],
            ["Challenge record", "Qualifying counter-evidence"],
          ]}
        />
      </RouteFrame>
    );
  }

  return (
    <div className="investigate-result-mode min-h-full py-6">
      <InvestigationWorkspace
        key={investigation.investigation_id}
        investigation={investigation}
        challengeBusy={work.challengeBusy}
        challengeError={work.challengeError}
        reelState={work.reelState}
        reelError={work.reelError}
        onChallenge={() => void work.runChallenge()}
        onGenerateReel={(ids) => void work.runReel(ids)}
      />
    </div>
  );
}

function ReelsRoute() {
  const { work } = useInvestigateContext();
  const investigation = work.investigation;

  if (investigation?.state !== "complete") {
    return (
      <RouteFrame
        eyebrow="Evidence reels"
        title="Compile only accepted source moments."
        copy="A reel becomes available after an investigation produces playable, source-locked evidence."
      >
        <RouteEmpty
          icon="film"
          title="No evidence sequence is available"
          copy="Run an investigation before compiling a chronological evidence reel."
          actionLabel="Start an investigation"
          actionHref="/investigate"
          details={[
            ["Eligibility", "Playable accepted moments"],
            ["Order", "Original source chronology"],
            ["Output", "Reviewable evidence cut"],
          ]}
        />
      </RouteFrame>
    );
  }

  const playableEventIds = investigation.shots
    .filter((shot) => shot.stream_url)
    .map((shot) => shot.event_id);

  return (
    <RouteFrame
      eyebrow="Evidence reels"
      title="Build the chronological source cut."
      copy="Only playable moments accepted by the evidence gate are eligible for compilation."
    >
      <ReelPanel
        events={investigation.events}
        shots={investigation.shots}
        selectedEventIds={playableEventIds}
        reel={investigation.reel}
        state={work.reelState}
        error={work.reelError}
        onGenerate={() => void work.runReel(playableEventIds)}
      />
    </RouteFrame>
  );
}

function PolicyRoute() {
  return (
    <RouteFrame
      eyebrow="Evidence policy"
      title="Accountability is part of the interface."
      copy="Strata separates retrieval, conclusion writing, and counter-evidence so unsupported certainty never looks like a finished answer."
      action={
        <Link href="/investigate" className="investigate-route-action">
          <Icon name="search" />
          Open investigation
        </Link>
      }
    >
      <section className="investigate-policy-hero">
        <span>
          <Icon name="shield" />
        </span>
        <div>
          <small>Source-lock rule</small>
          <h2>If the archive cannot establish it, Strata says so.</h2>
          <p>
            Every displayed factual sentence must name the event IDs that
            support it. Missing evidence is surfaced, never silently filled.
          </p>
        </div>
      </section>

      <div className="investigate-policy-grid">
        {[
          {
            number: "01",
            title: "Exact source windows",
            copy: "Claims remain attached to their original video, organization, date, and timestamp range.",
            icon: "play" as const,
          },
          {
            number: "02",
            title: "Sentence-level mapping",
            copy: "Each conclusion exposes the exact accepted events that support its wording.",
            icon: "inspect" as const,
          },
          {
            number: "03",
            title: "Separate challenge pass",
            copy: "Unused footage is searched independently for evidence that could qualify or revise the first answer.",
            icon: "spark" as const,
          },
        ].map((item) => (
          <article key={item.number}>
            <div>
              <span>{item.number}</span>
              <Icon name={item.icon} />
            </div>
            <h3>{item.title}</h3>
            <p>{item.copy}</p>
          </article>
        ))}
      </div>

      <section className="investigate-protocol-strip">
        {["Search", "Retrieve", "Compare", "Challenge", "Compile"].map(
          (step, index) => (
            <div key={step}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <p>{step}</p>
            </div>
          ),
        )}
      </section>
    </RouteFrame>
  );
}

function RouteFrame({
  eyebrow,
  title,
  copy,
  action,
  children,
}: {
  eyebrow: string;
  title: string;
  copy: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <main className="investigate-route-page">
      <header className="investigate-route-header">
        <div>
          <span>{eyebrow}</span>
          <h1>{title}</h1>
          <p>{copy}</p>
        </div>
        {action}
      </header>
      {children}
    </main>
  );
}

function RouteStat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: "archive" | "film" | "check";
}) {
  return (
    <article className="investigate-route-stat">
      <span>
        <Icon name={icon} />
      </span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

function RouteEmpty({
  icon,
  title,
  copy,
  actionLabel,
  actionHref,
  details,
}: {
  icon: "x" | "archive" | "inspect" | "film";
  title: string;
  copy: string;
  actionLabel?: string;
  actionHref?: string;
  details?: Array<[string, string]>;
}) {
  return (
    <section className="investigate-route-empty">
      <div className="investigate-route-empty-copy">
        <span>
          <Icon name={icon} />
        </span>
        <div>
          <h2>{title}</h2>
          <p>{copy}</p>
          {actionLabel && actionHref ? (
            <Link href={actionHref} className="investigate-route-action">
              {actionLabel}
              <Icon name="arrow" />
            </Link>
          ) : null}
        </div>
      </div>
      {details?.length ? (
        <div className="investigate-route-empty-ledger">
          {details.map(([label, value], index) => (
            <div key={label}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <p>{label}</p>
              <small>{value}</small>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
