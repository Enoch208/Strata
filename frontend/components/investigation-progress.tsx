import type { InvestigationState } from "@/lib/types";
import { progressCopy } from "@/lib/format";
import { Icon } from "./icon";

const stages = ["searching", "retrieving", "comparing", "building"] as const;

type ActiveState = (typeof stages)[number];

export function InvestigationProgress({ state }: { state: ActiveState }) {
  const activeIndex = stages.indexOf(state);

  return (
    <section className="mx-auto w-full max-w-[1500px] px-4 py-8 sm:px-6 lg:px-8">
      <div className="glass-panel animate-scale-in p-6 sm:p-8">
        <div className="flex items-center gap-3">
          <span className="processing-mark">
            <Icon name="spark" className="size-5" />
          </span>
          <div>
            <p className="eyebrow">
              <span className="tabular-nums text-white/80">02</span>
              <span className="eyebrow-rule" />
              <span>Investigation running</span>
            </p>
            <h2 className="mt-2 text-2xl font-light tracking-tight text-white sm:text-3xl">
              {progressCopy[state]}
            </h2>
          </div>
        </div>
        <div className="mt-8 grid gap-2 sm:grid-cols-4">
          {stages.map((stage, index) => (
            <div
              key={stage}
              className={`progress-step ${
                index < activeIndex
                  ? "progress-complete"
                  : index === activeIndex
                    ? "progress-active"
                    : ""
              }`}
            >
              <span className="progress-index tabular-nums">
                {index < activeIndex ? <Icon name="check" /> : `0${index + 1}`}
              </span>
              <span>{progressCopy[stage]}</span>
            </div>
          ))}
        </div>
        <div className="mt-7 h-1 overflow-hidden rounded-full bg-white/5">
          <div
            className="progress-bar"
            style={{ width: `${((activeIndex + 1) / stages.length) * 100}%` }}
          />
        </div>
      </div>
    </section>
  );
}

export function isProgressState(
  state: InvestigationState | null,
): state is ActiveState {
  return state !== null && stages.includes(state as ActiveState);
}
