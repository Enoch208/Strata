"use client";

import Hls from "hls.js";
import { useEffect, useRef, useState } from "react";
import { Icon } from "./icon";

type Props = {
  streamUrl: string | null;
  playerUrl: string | null;
  title: string;
};

export function MediaPlayer({ streamUrl, playerUrl, title }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [failedStream, setFailedStream] = useState<string | null>(null);
  const [useFallback, setUseFallback] = useState(false);
  const failed = failedStream === streamUrl;

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !streamUrl || useFallback) return;

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamUrl;
      return () => {
        video.removeAttribute("src");
        video.load();
      };
    }

    if (!Hls.isSupported()) {
      queueMicrotask(() => setFailedStream(streamUrl));
      return;
    }

    const hls = new Hls();
    hls.loadSource(streamUrl);
    hls.attachMedia(video);
    hls.on(Hls.Events.ERROR, (_, data) => {
      if (data.fatal) setFailedStream(streamUrl);
    });

    return () => hls.destroy();
  }, [streamUrl, useFallback]);

  if (!streamUrl) {
    return (
      <div className="player-empty">
        <span className="player-empty-icon">
          <Icon name="film" className="size-6" />
        </span>
        <p className="mt-4 text-sm font-medium text-white">Video playback failure</p>
        <p className="mt-1 max-w-sm text-center text-xs leading-5 text-white/40">
          This evidence window has no playable stream. Strata will not
          substitute or fabricate footage.
        </p>
      </div>
    );
  }

  if (useFallback && playerUrl) {
    return (
      <iframe
        src={playerUrl}
        title={`${title} — hosted evidence player`}
        allow="autoplay; fullscreen; picture-in-picture"
        allowFullScreen
        className="aspect-video w-full rounded-xl bg-black"
      />
    );
  }

  return (
    <div className="relative aspect-video overflow-hidden rounded-xl bg-black">
      <video
        ref={videoRef}
        controls
        playsInline
        preload="metadata"
        aria-label={`${title} evidence player`}
        onError={() => setFailedStream(streamUrl)}
        className="h-full w-full"
      >
        Your browser does not support video playback.
      </video>
      {failed ? (
        <div className="absolute inset-0 grid place-items-center bg-[#090b10]/95 p-6 text-center">
          <div>
            <span className="player-empty-icon mx-auto">
              <Icon name="film" className="size-6" />
            </span>
            <p className="mt-4 text-sm font-medium text-white">
              Direct stream playback failed
            </p>
            {playerUrl ? (
              <button
                onClick={() => setUseFallback(true)}
                className="secondary-button secondary-button-compact mt-4"
              >
                Use hosted fallback
                <Icon name="arrow" />
              </button>
            ) : (
              <p className="mt-2 text-xs text-white/40">
                No hosted fallback is available for this source.
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
