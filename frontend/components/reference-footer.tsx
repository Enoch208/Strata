import type { Archive } from "@/lib/types";

export function ReferenceFooter({ archive }: { archive: Archive | null }) {
  return (
    <footer className="relative z-10 mx-auto mt-20 max-w-7xl px-4 pb-12 sm:px-6">
      <div className="reference-footer animate-on-scroll">
        <div className="relative px-6 py-12 sm:px-10 lg:px-14 lg:py-16">
          <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-4">
              <p className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
                Strata
              </p>
              <p className="max-w-[28ch] text-sm tracking-tight text-white/70 sm:text-base">
                Git history for what people said—source-locked, challengeable,
                and playable.
              </p>
            </div>
            <FooterColumn
              title="Product"
              items={[
                ["Product", "#product"],
                ["System", "#capabilities"],
                ["Evidence policy", "#principles"],
              ]}
            />
            <div>
              <p className="text-xl font-semibold tracking-tight text-white">Archive</p>
              <p className="mt-4 text-sm leading-6 text-white/60">
                {archive?.title ?? "Artemis I Launch Archive"}
              </p>
            </div>
            <div>
              <p className="text-xl font-semibold tracking-tight text-white">Policy</p>
              <p className="mt-4 text-sm leading-6 text-white/60">
                Evidence before interpretation. No truth scores or accusations.
              </p>
            </div>
          </div>
          <p
            aria-hidden="true"
            className="mt-14 bg-gradient-to-t from-blue-600 to-slate-400 bg-clip-text text-center text-[15vw] font-semibold leading-none tracking-tighter text-transparent opacity-70 lg:text-[150px]"
          >
            STRATA
          </p>
          <div className="mt-10 h-px bg-white/10" />
          <div className="mt-6 flex flex-col gap-4 text-xs text-white/40 sm:flex-row sm:items-center sm:justify-between">
            <p>Built for source accountability.</p>
            <p>
              {archive?.acknowledgement ??
                "Source footage courtesy of NASA. NASA does not endorse this project."}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({
  title,
  items,
}: {
  title: string;
  items: Array<[string, string]>;
}) {
  return (
    <div>
      <p className="text-xl font-semibold tracking-tight text-white">{title}</p>
      <ul className="mt-4 space-y-3 text-sm text-white/70 sm:text-base">
        {items.map(([label, href]) => (
          <li key={label}>
            <a href={href} className="transition hover:text-white">
              {label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
