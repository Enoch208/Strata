import { Icon } from "./icon";

export function PrinciplesSection() {
  return (
    <div id="principles" className="reference-stage">
      <section className="reference-panel animate-on-scroll">
        <header className="reference-section-header">
          <div className="max-w-2xl">
            <p className="eyebrow">
              <span className="tabular-nums text-sm font-semibold text-white/80">03</span>
              <span className="eyebrow-rule" />
              <span>Evidence policy</span>
            </p>
            <h2 className="mt-2 text-left text-3xl tracking-tighter text-white sm:text-4xl md:text-5xl">
              Built for accountable answers
            </h2>
            <p className="mt-3 text-left text-sm tracking-tight text-white/70 sm:text-base">
              Conclusions stay inspectable, conservative, and tied to real footage.
            </p>
          </div>
        </header>
        <div className="mt-8 h-px bg-white/10" />

        <div className="mt-8 grid grid-cols-1 items-start gap-8 rounded-3xl border border-white/10 bg-white/5 p-6 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <div className="principle-visual principle-photo">
              <span className="absolute bottom-4 left-4 grid size-12 place-items-center rounded-xl bg-black/45 text-blue-200 ring-1 ring-white/15 backdrop-blur">
                <Icon name="shield" className="size-6" />
              </span>
            </div>
            <div className="mt-6">
              <p className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                Source lock
              </p>
              <p className="mt-1 text-sm tracking-tight text-white/60 sm:text-base">
                The evidence gate behind every conclusion
              </p>
            </div>
          </div>
          <div className="flex flex-col justify-between lg:col-span-8">
            <p className="text-4xl font-light leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
              “If the archive cannot establish it, Strata says so.”
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <PolicyChip text="Exact timestamps" />
              <PolicyChip text="Inspectable sentence map" />
              <PolicyChip text="Separate challenge pass" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function PolicyChip({ text }: { text: string }) {
  return (
    <span className="inline-flex h-11 items-center rounded-full bg-white/5 px-5 text-sm text-white/70 ring-1 ring-white/10">
      {text}
    </span>
  );
}
