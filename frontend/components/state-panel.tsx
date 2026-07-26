import { PrimaryButton, SecondaryButton } from "./button";
import { Icon } from "./icon";

type Props = {
  kind: "insufficient" | "failed";
  title: string;
  detail: string | null;
  onRetry: () => void;
};

export function StatePanel({ kind, title, detail, onRetry }: Props) {
  return (
    <section className="mx-auto w-full max-w-[1500px] px-4 py-8 sm:px-6 lg:px-8">
      <div className={`glass-panel state-panel ${kind === "insufficient" ? "tone-amber" : "tone-red"}`}>
        <span className="player-empty-icon">
          <Icon name={kind === "insufficient" ? "inspect" : "x"} className="size-5" />
        </span>
        <p className="eyebrow mt-5 justify-center">
          <span className="tabular-nums text-white/80">02</span>
          <span className="eyebrow-rule" />
          <span>{kind === "insufficient" ? "No relevant evidence" : "Investigation failed"}</span>
        </p>
        <h2 className="mt-4 text-2xl font-light tracking-tight text-white sm:text-3xl">
          {title}
        </h2>
        {detail ? (
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-white/45">
            {detail}
          </p>
        ) : null}
        {kind === "failed" ? (
          <SecondaryButton onClick={onRetry} className="mt-6">
            <Icon name="refresh" />
            Retry investigation
          </SecondaryButton>
        ) : (
          <PrimaryButton onClick={onRetry} className="mt-6">
            <Icon name="search" />
            Search again
          </PrimaryButton>
        )}
      </div>
    </section>
  );
}
