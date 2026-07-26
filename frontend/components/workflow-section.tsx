const steps: Array<{
  title: string;
  copy: string;
}> = [
  {
    title: "Ask the archive",
    copy: "Search speech, OCR, visual context, and indexed claim events across every source.",
  },
  {
    title: "Inspect the diff",
    copy: "Review the chronological trail and open the exact source window behind every finding.",
  },
  {
    title: "Challenge & compile",
    copy: "Run a separate counter-evidence pass, then compile chosen moments into a playable reel.",
  },
];

export function WorkflowSection() {
  return (
    <div id="workflow" className="reference-stage">
      <section className="reference-panel animate-on-scroll">
        <header className="reference-section-header">
          <div className="max-w-2xl">
            <p className="eyebrow">
              <span className="tabular-nums text-sm font-semibold text-white/80">02</span>
              <span className="eyebrow-rule" />
              <span>Workflow</span>
            </p>
            <h2 className="mt-2 text-left text-3xl tracking-tighter text-white sm:text-4xl md:text-5xl">
              How it works
            </h2>
            <p className="mt-3 text-left text-sm tracking-tight text-white/70 sm:text-base">
              From a temporal question to source-locked, challengeable evidence.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a href="#product" className="reference-secondary-link">
              Explore product
            </a>
            <a href="#principles" className="reference-outline-link">
              Evidence policy
            </a>
          </div>
        </header>
        <div className="mt-8 h-px bg-white/10" />

        <ol className="mt-8 grid grid-cols-1 items-stretch gap-8 lg:grid-cols-12">
          {steps.map((step, index) => (
            <li key={step.title} className="relative lg:col-span-4">
              <article className="reference-step-card">
                <StepVisual index={index} />
                <h3 className="mt-6 text-3xl tracking-tighter text-white">
                  {step.title}
                </h3>
                <p className="mb-6 mt-2 max-w-[52ch] text-sm leading-relaxed tracking-tight text-white/60 sm:text-base">
                  {step.copy}
                </p>
                <span className="reference-step-badge">
                  <span className="size-1.5 rounded-full bg-blue-300/90" />
                  <span className="uppercase text-white/70">Step</span>
                  <span className="tabular-nums font-semibold tracking-wider text-white">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </span>
              </article>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function StepVisual({ index }: { index: number }) {
  if (index === 0) {
    return (
      <div className="reference-step-visual workflow-step-image workflow-search-image">
        <div className="relative z-10 flex h-full flex-col justify-between">
          <span className="w-fit rounded-full border border-white/15 bg-black/55 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/75 backdrop-blur-md">
            Archive query
          </span>
          <div className="flex gap-2">
            {["Speech", "OCR", "Frames"].map((source) => (
              <span
                key={source}
                className="rounded-full border border-white/15 bg-black/55 px-3 py-1.5 text-[9px] uppercase tracking-[0.12em] text-white/65 backdrop-blur-md"
              >
                {source}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (index === 1) {
    return (
      <div className="reference-step-visual workflow-step-image workflow-archive-image">
        <div className="relative z-10 flex h-full flex-col justify-between">
          <span className="w-fit rounded-full border border-white/15 bg-black/55 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/75 backdrop-blur-md">
            Source chronology
          </span>
          <div className="grid grid-cols-4 gap-2">
            {["bg-blue-300", "bg-emerald-300", "bg-purple-300", "bg-amber-200"].map(
              (tone, frameIndex) => (
                <div
                  key={tone}
                  className="rounded-lg border border-white/15 bg-black/55 p-2 backdrop-blur-md"
                >
                  <span className={`block h-1 w-5 rounded ${tone}`} />
                  <span className="mt-2 block text-[9px] tabular-nums text-white/65">
                    T+{String(frameIndex + 1).padStart(2, "0")}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>
      </div>
    );
  }

  if (index === 2) {
    return (
      <div className="reference-step-visual workflow-step-image workflow-compile-image">
        <div className="relative z-10 flex h-full flex-col justify-between">
          <span className="w-fit rounded-full border border-emerald-300/20 bg-black/55 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-200/85 backdrop-blur-md">
            Challenge passed
          </span>
          <div className="flex items-center gap-2 rounded-xl border border-white/15 bg-black/60 p-2.5 backdrop-blur-md">
            <span className="size-2 rounded-full bg-blue-300" />
            <span className="h-px flex-1 bg-gradient-to-r from-blue-300 via-emerald-300 to-purple-300" />
            <span className="size-2 rounded-full bg-emerald-300" />
            <span className="text-[9px] uppercase tracking-[0.12em] text-white/65">
              Reel ready
            </span>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
