import { PreviewDetailsPanel } from "./preview-details-panel";
import { PreviewPlayerPanel } from "./preview-player-panel";
import { PreviewTimelinePanel } from "./preview-timeline-panel";

export function ProductPreview() {
  return (
    <div id="product" className="reference-stage">
      <section className="reference-panel animate-on-scroll">
        <header className="reference-section-header">
          <div className="max-w-2xl">
            <p className="eyebrow">
              <span className="tabular-nums text-sm font-semibold text-white/80">01</span>
              <span className="eyebrow-rule" />
              <span>Feature</span>
            </p>
            <h2 className="mt-2 text-left text-3xl tracking-tighter text-white sm:text-4xl md:text-5xl">
              Source-locked investigation
            </h2>
            <p className="mt-3 text-left text-sm tracking-tight text-white/70 sm:text-base">
              Trace a changing claim, inspect exact footage, and test the first conclusion.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a href="#workflow" className="reference-secondary-link">
              How it works
            </a>
            <a href="#principles" className="reference-outline-link">
              Evidence policy
            </a>
          </div>
        </header>

        <div className="reference-editor">
          <div className="editor-topbar">
            <div className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-full bg-red-500/80" />
              <span className="size-2.5 rounded-full bg-yellow-400/80" />
              <span className="size-2.5 rounded-full bg-green-500/80" />
            </div>
            <span>Strata · Investigation workspace</span>
          </div>
          <div className="grid min-h-[660px] md:grid-cols-12">
            <PreviewTimelinePanel />
            <PreviewPlayerPanel />
            <PreviewDetailsPanel />
          </div>
        </div>
      </section>
    </div>
  );
}
