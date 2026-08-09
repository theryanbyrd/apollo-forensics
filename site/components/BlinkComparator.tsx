"use client";

// The claim-4 blink comparison is real evidence, not decoration, so it plays by
// default. But it is a 2-frame loop that never ends, which WCAG 2.2.2 requires a
// pause control for, and vestibular users need it suppressed: under
// prefers-reduced-motion it starts on the static frame and only animates on request.

import Image from "next/image";
import { useEffect, useState } from "react";
import { Pause, Play } from "@phosphor-icons/react";

const W = 1600;
const H = 446;

export default function BlinkComparator() {
  const [playing, setPlaying] = useState(true);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) setPlaying(false);
    setReady(true);
  }, []);

  return (
    <div className="relative overflow-hidden rounded-xl border border-neutral-800">
      {playing && ready ? (
        <Image
          src="/figures/04-backdrop-parallax.gif"
          alt="Two Apollo 15 photographs aligned and alternating: the same distant mountains with the Lunar Module present in one frame and absent in the other."
          width={W}
          height={H}
          unoptimized
          priority
          className="w-full"
        />
      ) : (
        <Image
          src="/figures/04-backdrop-parallax-still.jpg"
          alt="One frame of the Apollo 15 pair: distant mountains above the lunar surface, with the Lunar Module present."
          width={W}
          height={H}
          priority
          className="w-full"
        />
      )}
      <button
        type="button"
        onClick={() => setPlaying((p) => !p)}
        aria-pressed={playing}
        className="absolute bottom-2 right-2 inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-neutral-600 bg-neutral-950/85 px-3 text-xs font-semibold text-neutral-100 backdrop-blur transition-colors hover:border-neutral-400"
      >
        {playing ? (
          <>
            <Pause size={12} weight="fill" aria-hidden /> Pause blink
          </>
        ) : (
          <>
            <Play size={12} weight="fill" aria-hidden /> Play blink
          </>
        )}
      </button>
    </div>
  );
}
