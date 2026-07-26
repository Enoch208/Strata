import { useState } from "react";
import { PrimaryButton } from "./button";
import { Icon } from "./icon";

export const SEEDED_QUERY =
  "Did the September 3 hydrogen leak fully explain why Artemis I launched in November? Trace the evidence.";

type Props = {
  disabled: boolean;
  busy: boolean;
  onSubmit: (query: string) => void;
};

export function QueryComposer({ disabled, busy, onSubmit }: Props) {
  const [query, setQuery] = useState(SEEDED_QUERY);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    if (value && !disabled && !busy) onSubmit(value);
  }

  return (
    <form onSubmit={submit} className="query-shell">
      <label htmlFor="archive-query" className="sr-only">
        Ask a question across the archive
      </label>
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <Icon name="search" className="mt-1 size-5 shrink-0 text-white/35" />
        <textarea
          id="archive-query"
          rows={2}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={busy}
          placeholder="Ask how a claim, deadline, or explanation changed…"
          className="min-h-[54px] min-w-0 flex-1 resize-none bg-transparent text-[15px] leading-6 text-white outline-none placeholder:text-white/25 disabled:cursor-wait"
        />
      </div>
      <PrimaryButton type="submit" disabled={disabled || busy || !query.trim()}>
        {busy ? "Investigating…" : "Investigate archive"}
        <Icon name="arrow" />
      </PrimaryButton>
    </form>
  );
}
