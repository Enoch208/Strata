"use client";

import Script from "next/script";

declare global {
  interface Window {
    UnicornStudio?: {
      init: () => void;
      isInitialized?: boolean;
    };
  }
}

export function UnicornBackground() {
  return (
    <>
      <div
        className="unicorn-background"
        style={{
          maskImage:
            "linear-gradient(to bottom, transparent, black 0%, black 47%, transparent)",
          WebkitMaskImage:
            "linear-gradient(to bottom, transparent, black 0%, black 47%, transparent)",
        }}
      >
        <div
          data-us-project="3eLGLP7pmQS4ozfklmrX"
          className="absolute inset-0 size-full"
        />
      </div>
      <Script
        src="https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.4.29/dist/unicornStudio.umd.js"
        strategy="afterInteractive"
        onLoad={() => {
          if (window.UnicornStudio && !window.UnicornStudio.isInitialized) {
            window.UnicornStudio.init();
            window.UnicornStudio.isInitialized = true;
          }
        }}
      />
    </>
  );
}
