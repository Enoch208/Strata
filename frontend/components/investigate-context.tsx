"use client";

import {
  createContext,
  useContext,
  useEffect,
  type ReactNode,
} from "react";
import { useArchive } from "@/hooks/use-archive";
import { useInvestigation } from "@/hooks/use-investigation";

type InvestigateContextValue = {
  archiveState: ReturnType<typeof useArchive>;
  work: ReturnType<typeof useInvestigation>;
  canInvestigate: boolean;
  investigate: (query: string) => void;
};

const InvestigateContext = createContext<InvestigateContextValue | null>(null);

export function InvestigateProvider({ children }: { children: ReactNode }) {
  const archiveState = useArchive();
  const work = useInvestigation();
  const canInvestigate = Boolean(archiveState.archive);

  function investigate(query: string) {
    if (archiveState.archive) {
      void work.investigate(archiveState.archive, query);
    }
  }

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.08 },
    );
    document
      .querySelectorAll(".animate-on-scroll")
      .forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [work.investigation, work.progress]);

  return (
    <InvestigateContext.Provider
      value={{ archiveState, work, canInvestigate, investigate }}
    >
      {children}
    </InvestigateContext.Provider>
  );
}

export function useInvestigateContext() {
  const context = useContext(InvestigateContext);
  if (!context) {
    throw new Error(
      "useInvestigateContext must be used inside InvestigateProvider.",
    );
  }
  return context;
}
