"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon, type IconName } from "./icon";
import { useInvestigateContext } from "./investigate-context";

const navigation: Array<{
  label: string;
  href: string;
  icon: IconName;
}> = [
  { label: "Investigation", href: "/investigate", icon: "search" },
  { label: "Archive sources", href: "/investigate/sources", icon: "archive" },
  { label: "Evidence", href: "/investigate/evidence", icon: "inspect" },
  { label: "Evidence reels", href: "/investigate/reels", icon: "film" },
  { label: "Evidence policy", href: "/investigate/policy", icon: "shield" },
];

const routeTitles: Record<string, { title: string; eyebrow: string }> = {
  "/investigate": {
    title: "Investigation workspace",
    eyebrow: "Source-locked archive",
  },
  "/investigate/sources": {
    title: "Archive sources",
    eyebrow: "First-party source manifest",
  },
  "/investigate/evidence": {
    title: "Evidence workspace",
    eyebrow: "Claims, citations, and exact moments",
  },
  "/investigate/reels": {
    title: "Evidence reels",
    eyebrow: "Chronological source compilation",
  },
  "/investigate/policy": {
    title: "Evidence policy",
    eyebrow: "Source-lock and challenge protocol",
  },
};

export function InvestigateShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { archiveState } = useInvestigateContext();
  const { archive, health, loading, error } = archiveState;
  const connected = health?.videodb === "connected" || Boolean(archive);
  const archiveStatus =
    archive?.index_status === "ready"
      ? "Archive live"
      : archive
        ? "Archive partial"
        : "Archive offline";
  const heading = routeTitles[pathname] ?? routeTitles["/investigate"];

  return (
    <div className="investigate-dashboard">
      <div className="investigate-shell">
        <aside className="investigate-sidebar">
          <div>
            <Link href="/" className="investigate-brand">
              <span className="investigate-brand-mark">
                <span />
                <span />
                <span />
              </span>
              <span>
                <strong>Strata</strong>
                <small>Intelligence</small>
              </span>
            </Link>

            <p className="investigate-nav-label">Workspace</p>
            <nav
              className="investigate-nav"
              aria-label="Investigation workspace"
            >
              {navigation.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={active ? "investigate-nav-active" : ""}
                    aria-current={active ? "page" : undefined}
                  >
                    <Icon name={item.icon} />
                    <span>{item.label}</span>
                    {active ? <span className="investigate-nav-pulse" /> : null}
                  </Link>
                );
              })}
            </nav>

            <p className="investigate-nav-label investigate-nav-label-general">
              General
            </p>
            <nav className="investigate-nav" aria-label="General navigation">
              <Link href="/">
                <Icon name="arrow" className="rotate-180" />
                <span>Back to website</span>
              </Link>
            </nav>
          </div>

          <div className="investigate-sidebar-footer">
            <div className="investigate-sync-card">
              <span className={connected ? "is-ready" : ""}>
                <Icon name={connected ? "check" : "refresh"} />
              </span>
              <div>
                <strong>
                  {connected ? "Archive connected" : "Connecting archive"}
                </strong>
                <small>
                  {archive
                    ? `${archive.index_status} index · ${archive.stats.video_count} sources`
                    : "Source-lock service"}
                </small>
              </div>
            </div>
            <Link href="/" className="investigate-exit">
              <Icon name="arrow" className="rotate-180" />
              Exit workspace
            </Link>
          </div>
        </aside>

        <section className="investigate-workspace-surface">
          <header className="investigate-topbar">
            <div className="investigate-topbar-title">
              <Link href="/" aria-label="Back to Strata">
                <Icon name="chevron" className="rotate-90" />
              </Link>
              <div>
                <p>{heading.title}</p>
                <span>{archive?.title ?? heading.eyebrow}</span>
              </div>
            </div>

            <div className="investigate-topbar-actions">
              {error ? (
                <button
                  type="button"
                  className="investigate-alert-button"
                  onClick={() => void archiveState.load()}
                >
                  <Icon name="refresh" />
                  Retry connection
                </button>
              ) : (
                <span
                  className={`investigate-connection ${
                    connected ? "is-connected" : ""
                  }`}
                >
                  <span />
                  {loading && !archive
                    ? "Connecting"
                    : connected
                      ? archiveStatus
                      : "Archive offline"}
                </span>
              )}
              <span className="investigate-avatar">SA</span>
              <div className="investigate-user">
                <strong>Strata Analyst</strong>
                <small>Investigation desk</small>
              </div>
            </div>
          </header>

          <div className="investigate-scroll-area">{children}</div>
        </section>
      </div>
    </div>
  );
}
