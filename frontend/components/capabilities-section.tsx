import { Icon } from "./icon";

const included = {
  trail: [
    "Chronological claim-event timeline",
    "Exact video and timestamp windows",
    "Inspectable sentence-to-event mapping",
  ],
  challenge: [
    "Separate counter-evidence retrieval",
    "New-source novelty inspection",
    "Playable chronological evidence reel",
  ],
} as const;

export function CapabilitiesSection() {
  return (
    <div id="capabilities" className="reference-stage">
      <section className="reference-panel animate-on-scroll">
        <header className="reference-section-header">
          <div className="max-w-2xl">
            <p className="eyebrow">
              <span className="tabular-nums text-sm font-semibold text-white/80">04</span>
              <span className="eyebrow-rule" />
              <span>System</span>
            </p>
            <h2 className="mt-2 text-left text-3xl tracking-tighter text-white sm:text-4xl md:text-5xl">
              One accountable workflow
            </h2>
            <p className="mt-3 text-left text-sm tracking-tight text-white/70 sm:text-base">
              From archive-wide retrieval to the final playable evidence packet.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a href="#product" className="reference-secondary-link">
              Product preview
            </a>
            <a href="#principles" className="reference-outline-link">
              Read the policy
            </a>
          </div>
        </header>
        <div className="h-px bg-white/10" />

        <div className="grid grid-cols-1 gap-6 pt-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-5">
            <SystemStep
              number="1"
              title="Retrieve"
              copy="Search every indexed source and hydrate exact playable moments."
            />
            <SystemStep
              number="2"
              title="Compare"
              copy="Arrange accepted statements over time and expose what changed."
            />
            <SystemStep
              number="3"
              title="Challenge"
              copy="Run a second archive-wide pass before compiling the evidence."
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:col-span-7 lg:grid-cols-2">
            <CapabilityCard
              eyebrow="Evidence trail"
              title="Source"
              subtitle="Every conclusion stays attached to footage."
              features={included.trail}
              icon="inspect"
            />
            <CapabilityCard
              eyebrow="Adversarial pass"
              title="Challenge"
              subtitle="The first plausible answer is never treated as final."
              features={included.challenge}
              icon="spark"
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function SystemStep({
  number,
  title,
  copy,
}: {
  number: string;
  title: string;
  copy: string;
}) {
  return (
    <article className="system-step-card">
      <div className="flex items-center gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/15 text-sm text-white/80 ring-1 ring-white/20">
          {number}
        </span>
        <h3 className="text-3xl font-light tracking-tighter text-white sm:text-4xl">
          {title}
        </h3>
      </div>
      <p className="mt-3 max-w-[56ch] text-sm tracking-tight text-white/60 sm:text-base">
        {copy}
      </p>
    </article>
  );
}

function CapabilityCard({
  eyebrow,
  title,
  subtitle,
  features,
  icon,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  features: readonly string[];
  icon: "inspect" | "spark";
}) {
  return (
    <article className="capability-card">
      <div className="flex items-start justify-between">
        <p className="text-xl font-medium tracking-tight text-white">{eyebrow}</p>
        <span className="grid size-9 place-items-center rounded-xl bg-blue-500/10 text-blue-300 ring-1 ring-blue-400/20">
          <Icon name={icon} className="size-4" />
        </span>
      </div>
      <div className="mt-8">
        <p className="text-4xl font-light tracking-tighter text-white sm:text-6xl">
          {title}
        </p>
        <p className="mt-2 text-sm leading-5 text-white/50">{subtitle}</p>
      </div>
      <div className="mt-8 flex-1">
        <p className="text-sm font-medium text-white/85">What&apos;s included</p>
        <ul className="mt-4 space-y-3">
          {features.map((feature) => (
            <li key={feature} className="flex items-center gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-white/5 text-white/75 ring-1 ring-white/10">
                <Icon name="check" className="size-3.5" />
              </span>
              <span className="text-sm tracking-tight text-white/70">{feature}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-8 border-t border-white/10 pt-4">
        <a href="#product" className="reference-cta w-full">
          <span className="reference-cta-glow" />
          <span className="reference-cta-surface" />
          <span className="reference-cta-highlight" />
          <span className="relative z-10">Explore the workflow</span>
        </a>
      </div>
    </article>
  );
}
