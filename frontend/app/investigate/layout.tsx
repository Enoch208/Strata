import type { ReactNode } from "react";
import { InvestigateProvider } from "@/components/investigate-context";
import { InvestigateShell } from "@/components/investigate-shell";

export default function InvestigateLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <InvestigateProvider>
      <InvestigateShell>{children}</InvestigateShell>
    </InvestigateProvider>
  );
}
