import { Icon, type IconName } from "./icon";

const actions: Array<{
  icon: IconName;
  title: string;
  copy: string;
  tone: string;
}> = [
  {
    icon: "search",
    title: "Search every source",
    copy: "Speech, OCR, and visual context",
    tone: "text-blue-300",
  },
  {
    icon: "archive",
    title: "Retrieve exact moments",
    copy: "Source video and timestamp window",
    tone: "text-emerald-300",
  },
  {
    icon: "inspect",
    title: "Compare over time",
    copy: "Dates, status, and explanations",
    tone: "text-purple-300",
  },
];

export function PreviewTimelinePanel() {
  return (
    <aside className="hidden border-r border-white/10 bg-black/30 md:col-span-3 md:flex md:flex-col">
      <div className="border-b border-white/10 px-4 py-3">
        <span className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
          <Icon name="spark" className="size-4" />
          Archive Agent
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <p className="mb-3 text-base font-light tracking-tight text-white sm:text-lg">
          How can the archive help?
        </p>
        <div className="space-y-2.5">
          {actions.map((action) => (
            <div
              key={action.title}
              className="flex items-center gap-3 rounded-lg bg-white/5 px-3 py-2.5 ring-1 ring-white/10"
            >
              <span className={`grid size-8 shrink-0 place-items-center rounded-md bg-white/8 ring-1 ring-white/10 ${action.tone}`}>
                <Icon name={action.icon} className="size-4" />
              </span>
              <div>
                <p className="text-left text-[13px] tracking-tight text-white">
                  {action.title}
                </p>
                <p className="mt-0.5 text-left text-[10px] tracking-tight text-white/40">
                  {action.copy}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 space-y-3">
          <div className="max-w-[90%] rounded-xl bg-white/5 p-3 ring-1 ring-white/10">
            <p className="text-xs leading-5 tracking-tight text-white/60">
              Ask how a deadline, forecast, or official explanation changed.
            </p>
          </div>
          <div className="ml-auto max-w-[90%] rounded-xl bg-blue-600/80 p-3 ring-1 ring-white/10">
            <p className="text-xs leading-5 tracking-tight text-white">
              Trace the sequence and show every exact source moment.
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">
          <div className="min-h-20 text-xs leading-5 text-white/35">
            Ask the archive a temporal question…
          </div>
          <span className="ml-auto grid size-8 place-items-center rounded-lg bg-blue-600 text-white">
            <Icon name="send" className="size-3.5" />
          </span>
        </div>
      </div>

      <div className="border-t border-white/10 px-4 py-3">
        <div className="flex items-center gap-2 text-[10px] text-emerald-400">
          <span className="status-dot" />
          Source mapping ready
        </div>
      </div>
    </aside>
  );
}
