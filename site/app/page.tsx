import Link from "next/link";
import Image from "next/image";
import claims from "@/data/claims.json";

type Claim = {
  num: number;
  slug: string;
  title: string;
  claim: string;
  test: string;
  verdict: string;
  headline: string;
  detail: string;
  falsification: string;
  figure: string;
  figureAlt: string;
  repoPath: string;
};

const REPO = "https://github.com/theryanbyrd/apollo-forensics";

export default function Home() {
  const items = claims as Claim[];
  return (
    <main className="mx-auto max-w-6xl px-4 py-12">
      <header className="mx-auto max-w-3xl text-center">
        <p className="text-[11px] uppercase tracking-[0.3em] text-el/70">Apollo Forensics</p>
        <h1 className="mt-3 text-4xl font-bold leading-tight sm:text-5xl">
          12 hoax claims. 12 falsifiable tests. <span className="text-el">Zero survived.</span>
        </h1>
        <p className="mt-4 text-base leading-relaxed opacity-80">
          Every moon-landing hoax claim that can be tested purely in software — tested. Real public data, explicit
          falsification criteria, verdicts from the numbers. A test that can&apos;t fail isn&apos;t a test: every
          experiment below could have come out for the conspiracy. None did.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/mission"
            className="rounded-md bg-el px-4 py-2 text-sm font-bold text-black transition-transform hover:scale-105"
          >
            ☾ Replay Apollo 11 on the real computer
          </Link>
          <a
            href={REPO}
            className="rounded-md border border-neutral-600 px-4 py-2 text-sm font-semibold opacity-90 hover:border-neutral-400"
          >
            All code &amp; data on GitHub →
          </a>
        </div>
      </header>

      <section className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((c) => (
          <article
            key={c.num}
            id={`claim-${c.num}`}
            className="group flex flex-col overflow-hidden rounded-lg border border-neutral-700/60 bg-neutral-900/40 transition-colors hover:border-neutral-500"
          >
            <div className="relative aspect-[16/10] overflow-hidden bg-black">
              <Image
                src={`/figures/${c.figure}`}
                alt={c.figureAlt}
                fill
                sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                className="object-cover transition-transform duration-500 group-hover:scale-105"
              />
              <span
                className={`absolute left-3 top-3 rounded px-2 py-0.5 text-[10px] font-bold tracking-widest ${
                  c.verdict === "REFUTED" ? "bg-red-500/90 text-white" : "bg-el/90 text-black"
                }`}
              >
                {c.verdict}
              </span>
            </div>
            <div className="flex flex-1 flex-col p-4">
              <div className="text-[10px] uppercase tracking-widest opacity-50">Claim #{c.num}</div>
              <h2 className="mt-1 text-lg font-bold leading-snug">{c.title}</h2>
              <p className="mt-2 text-sm italic opacity-70">“{c.claim}”</p>
              <p className="mt-3 text-sm leading-relaxed opacity-90">{c.test}</p>
              <p className="mt-3 rounded-md border border-el/20 bg-el/5 p-3 text-sm font-medium leading-relaxed">
                {c.headline}
              </p>
              <details className="mt-3 text-sm opacity-80">
                <summary className="cursor-pointer text-xs uppercase tracking-widest opacity-60 hover:opacity-100">
                  Detail &amp; how it could have failed
                </summary>
                <p className="mt-2 leading-relaxed">{c.detail}</p>
                <p className="mt-2 leading-relaxed">
                  <span className="font-semibold">Falsification criterion:</span> {c.falsification}
                </p>
              </details>
              <div className="mt-auto pt-4">
                <a
                  href={`${REPO}/tree/main/${c.repoPath}`}
                  className="text-sm font-semibold text-el underline-offset-4 hover:underline"
                >
                  Code, data &amp; full writeup →
                </a>
              </div>
            </div>
          </article>
        ))}
      </section>

      <section className="mx-auto mt-16 max-w-3xl rounded-lg border border-neutral-700/60 bg-neutral-900/40 p-6 text-center">
        <h2 className="text-xl font-bold">Hear the Moon answer back</h2>
        <p className="mt-2 text-sm leading-relaxed opacity-80">
          From claim #22: CapCom&apos;s voice, leaking through the astronauts&apos; headsets, returns to Houston{" "}
          <span className="font-semibold text-el">2.644 ± 0.035 seconds</span> after he speaks — the Earth–Moon
          round-trip at the speed of light, measured across 43 transmissions in the EVA tape.
        </p>
        <audio controls preload="none" src="/figures/echo_example.wav" className="mx-auto mt-4 w-full max-w-md" />
      </section>

      <footer className="mt-16 text-center text-xs opacity-60">
        <p>
          Built with Claude Code · methodology from “The Moon Landing Verification Playbook” ·{" "}
          <a className="underline" href={REPO}>
            github.com/theryanbyrd/apollo-forensics
          </a>
        </p>
      </footer>
    </main>
  );
}
