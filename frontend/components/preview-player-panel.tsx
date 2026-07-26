import { Icon } from "./icon";

const phases = ["Search", "Retrieve", "Compare", "Challenge"] as const;

export function PreviewPlayerPanel() {
  return (
    <main className="flex flex-col bg-black/20 md:col-span-6">
      <div className="panel-toolbar">
        <span>Evidence Player</span>
        <div className="flex items-center gap-2 text-emerald-400">
          <span className="status-dot" />
          Source locked
        </div>
      </div>
      <div className="flex items-center justify-between border-b border-white/10 bg-black/10 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="grid size-8 place-items-center rounded border border-white/10 bg-blue-600 text-white">
            <Icon name="search" className="size-3.5" />
          </span>
          <span className="text-xs text-white/45">Exact source workspace</span>
        </div>
        <div className="flex gap-2">
          <span className="rounded border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] text-white/45">
            Transcript
          </span>
          <span className="rounded border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] text-white/45">
            Source map
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-4">
        <div className="preview-player reference-media-player">
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-black/20" />
          <div className="absolute left-4 top-4 rounded-full bg-black/45 px-3 py-1 text-[10px] text-white/55 ring-1 ring-white/10 backdrop-blur">
            Official archive source
          </div>
          <div className="absolute bottom-16 left-4 max-w-sm">
            <p className="text-lg font-light tracking-tight text-white">
              Exact source moment
            </p>
            <p className="mt-1 text-[11px] leading-5 text-white/55">
              Source title, publication date, and evidence transcript stay visible.
            </p>
          </div>
          <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
            <span className="rounded-full bg-black/50 px-3 py-1 text-[10px] text-white/55 ring-1 ring-white/10 backdrop-blur">
              Source title · publication date
            </span>
            <span className="rounded-full bg-black/50 px-3 py-1 text-[10px] text-emerald-300 ring-1 ring-white/10 backdrop-blur">
              Playable evidence
            </span>
          </div>
        </div>

        <div className="preview-timeline">
          <div className="grid grid-cols-4 border-b border-white/10 px-3 py-2 text-center text-[8px] uppercase tracking-wider text-white/25">
            {phases.map((phase) => (
              <span key={phase}>{phase}</span>
            ))}
          </div>
          <div className="space-y-2 p-3">
            <div className="flex h-10 items-center gap-1 overflow-hidden rounded bg-white/4 p-1 ring-1 ring-white/8">
              <span className="reference-thumb reference-thumb-one" />
              <span className="reference-thumb reference-thumb-two" />
              <span className="reference-thumb reference-thumb-three ring-2 ring-amber-200/70" />
              <span className="reference-thumb reference-thumb-four" />
            </div>
            <Track tone="bg-emerald-500/30" left="ml-[27%]" width="w-[48%]" />
            <Track tone="bg-purple-500/30" left="ml-[54%]" width="w-[32%]" />
          </div>
          <div className="flex items-center justify-between border-t border-white/10 px-3 py-2">
            <span className="text-[9px] text-white/30">Chronological evidence trail</span>
            <div className="flex gap-1.5">
              <span className="rounded bg-white/5 px-2 py-1 text-[9px] text-white/40">Add to reel</span>
              <span className="rounded bg-blue-600 px-2 py-1 text-[9px] text-white">Inspect</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

function Track({
  tone,
  left,
  width,
}: {
  tone: string;
  left: string;
  width: string;
}) {
  return (
    <div className="h-8 overflow-hidden rounded bg-white/4 p-1 ring-1 ring-white/8">
      <span className={`block h-full rounded ${tone} ${left} ${width}`} />
    </div>
  );
}
