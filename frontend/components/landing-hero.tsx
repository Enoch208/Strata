import Link from "next/link";

export function LandingHero() {
  return (
    <section id="top" className="reference-hero">
      <div className="relative z-10 mx-auto w-full max-w-7xl px-6 pb-16">
        <div className="grid grid-cols-1 items-end gap-10 md:grid-cols-12">
          <div className="animate-fade-slide animation-delay-200 my-6 max-w-2xl space-y-6 md:col-span-4">
            <h1 className="text-4xl font-light leading-tight tracking-tighter text-white md:text-5xl">
              See How the Story Changed.
            </h1>
            <p className="text-base font-light leading-relaxed tracking-tight text-white/60 md:text-lg">
              Ask a question across hours of archived footage. Strata finds
              every version, cites the exact moments, and builds the evidence reel.
            </p>
            <Link href="/investigate" className="reference-cta reference-cta-large">
              <span className="reference-cta-glow" />
              <span className="reference-cta-surface" />
              <span className="reference-cta-highlight" />
              <span className="relative z-10">Investigate archive</span>
            </Link>
          </div>

          <div className="animate-fade-slide animation-delay-200 md:col-span-5" />

          <div className="animate-fade-slide animation-delay-300 flex w-full flex-col gap-6 md:col-span-3 md:items-end">
            <Pillar title="Exact" label="Source moments" />
            <Pillar title="Full" label="Archive search" />
            <Pillar title="Second" label="Challenge pass" />
          </div>
        </div>
      </div>
    </section>
  );
}

function Pillar({ title, label }: { title: string; label: string }) {
  return (
    <div className="w-full md:max-w-[190px]">
      <p className="text-left text-4xl font-light tracking-tighter text-white md:text-5xl">
        {title}
      </p>
      <p className="text-left text-sm font-light tracking-tight text-white/60 md:text-base">
        {label}
      </p>
    </div>
  );
}
