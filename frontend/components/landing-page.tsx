import { CapabilitiesSection } from "./capabilities-section";
import { LandingHeader } from "./landing-header";
import { LandingHero } from "./landing-hero";
import { PrinciplesSection } from "./principles-section";
import { ProductPreview } from "./product-preview";
import { ReferenceFooter } from "./reference-footer";
import { RevealObserver } from "./reveal-observer";
import { UnicornBackground } from "./unicorn-background";
import { WorkflowSection } from "./workflow-section";

export function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <UnicornBackground />
      <RevealObserver />
      <LandingHeader />
      <LandingHero />
      <ProductPreview />
      <WorkflowSection />
      <PrinciplesSection />
      <CapabilitiesSection />
      <ReferenceFooter archive={null} />
    </div>
  );
}
