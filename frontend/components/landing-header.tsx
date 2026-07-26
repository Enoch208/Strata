import Link from "next/link";
import { Icon } from "./icon";

export function LandingHeader() {
  return (
    <header className="absolute left-0 top-0 z-30 w-full animate-fade-slide">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <a href="#top" className="inline-flex items-center gap-3">
          <span className="reference-logo">
            <span className="reference-logo-line" />
          </span>
          <span className="text-sm font-medium tracking-tight text-white">
            Strata
          </span>
        </a>

        <div className="flex items-center gap-3">
          <div className="hidden items-center md:flex">
            <a href="#product" className="reference-nav-link">
              Product
            </a>
            <a href="#workflow" className="reference-nav-link">
              How it works
            </a>
            <a href="#principles" className="reference-nav-link">
              Evidence policy
            </a>
          </div>
          <Link href="/investigate" className="reference-cta">
            <span className="reference-cta-glow" />
            <span className="reference-cta-surface" />
            <span className="reference-cta-highlight" />
            <span className="relative z-10 inline-flex items-center gap-2">
              Explore Strata <Icon name="arrow" className="size-3.5" />
            </span>
          </Link>
        </div>
      </nav>
    </header>
  );
}
