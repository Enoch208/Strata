import { Icon } from "./icon";

export function PreviewDetailsPanel() {
  return (
    <aside className="hidden border-l border-white/10 bg-black/30 md:col-span-3 md:flex md:flex-col">
      <div className="border-b border-white/10 px-4 py-3">
        <span className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
          <Icon name="inspect" className="size-4" />
          Evidence Inspector
        </span>
      </div>
      <div className="flex gap-1 border-b border-white/10 px-4 py-3">
        <span className="rounded bg-blue-600 px-3 py-1.5 text-[10px] text-white">Source</span>
        <span className="rounded bg-white/5 px-3 py-1.5 text-[10px] text-white/40">Mapping</span>
        <span className="rounded bg-white/5 px-3 py-1.5 text-[10px] text-white/40">Challenge</span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        <PreviewCard title="Current source">
          <div className="space-y-2">
            <Bar width="w-full" />
            <Bar width="w-4/5" />
            <Bar width="w-2/3" />
          </div>
          <div className="mt-4 flex justify-between text-[9px] text-white/30">
            <span>Source organization</span>
            <span>Exact window</span>
          </div>
        </PreviewCard>

        <PreviewCard title="Sentence mapping">
          <div className="space-y-2">
            <MapRow tone="bg-blue-400" />
            <MapRow tone="bg-emerald-400" />
            <MapRow tone="bg-purple-400" />
          </div>
        </PreviewCard>

        <PreviewCard title="Challenge pass">
          <div className="rounded-lg bg-emerald-500/10 p-3 ring-1 ring-emerald-400/20">
            <div className="flex items-center gap-2 text-[10px] text-emerald-300">
              <span className="status-dot" />
              New source reached
            </div>
            <p className="mt-2 text-[9px] leading-4 text-white/35">
              Separate retrieval can qualify or revise the first conclusion.
            </p>
          </div>
        </PreviewCard>

        <PreviewCard title="Evidence policy">
          <div className="flex items-start gap-2">
            <Icon name="shield" className="mt-0.5 size-3.5 shrink-0 text-blue-300" />
            <p className="text-[10px] leading-4 text-white/40">
              Unsupported wording is withheld instead of filled with model knowledge.
            </p>
          </div>
        </PreviewCard>
      </div>
      <div className="flex gap-2 border-t border-white/10 p-4">
        <span className="flex-1 rounded bg-blue-600 px-3 py-2 text-center text-[10px] text-white">
          Generate reel
        </span>
        <span className="rounded bg-white/5 px-3 py-2 text-[10px] text-white/45 ring-1 ring-white/10">
          Export
        </span>
      </div>
    </aside>
  );
}

function PreviewCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg bg-white/5 p-3">
      <p className="mb-3 text-xs text-white/60">{title}</p>
      {children}
    </div>
  );
}

function Bar({ width }: { width: string }) {
  return <span className={`block h-1.5 rounded bg-white/10 ${width}`} />;
}

function MapRow({ tone }: { tone: string }) {
  return (
    <div className="flex items-center gap-2 rounded bg-black/15 p-2">
      <span className={`size-1.5 rounded-full ${tone}`} />
      <span className="h-1.5 flex-1 rounded bg-white/10" />
      <span className="h-4 w-8 rounded bg-white/8" />
    </div>
  );
}
