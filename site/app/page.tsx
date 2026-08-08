import Link from "next/link";
import Image from "next/image";
import { ArrowRight, MoonStars, Waveform } from "@phosphor-icons/react/dist/ssr";
import claims from "@/data/claims.json";
import Reveal from "@/components/Reveal";

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
const FEATURED = new Set([22, 15]);

function ClaimCard({ c, featured }: { c: Claim; featured: boolean }) {
  return (
    <article
      id={`claim-${c.num}`}
      className={`group flex flex-col overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900/40 transition-colors hover:border-neutral-600 ${
        featured ? "sm:col-span-2" : ""
      }`}
    >
      <div className={`relative overflow-hidden bg-neutral-950 ${featured ? "aspect-[2/1]" : "aspect-[16/10]"}`}>
        <Image
          src={`/figures/${c.figure}`}
          alt={c.figureAlt}
          fill
          sizes={featured ? "(max-width: 640px) 100vw, 66vw" : "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"}
          className="object-cover transition-transform duration-500 group-hover:scale-[1.03]"
        />
        <span
          className={`absolute left-3 top-3 rounded-md px-2 py-0.5 text-[10px] font-bold tracking-widest ${
            c.verdict === "REFUTED" ? "bg-red-500/90 text-white" : "bg-el/90 text-neutral-950"
          }`}
        >
          {c.verdict}
        </span>
      </div>
      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-bold leading-snug">{c.title}</h2>
          <span className="dseg ml-3 shrink-0 text-sm text-neutral-600">{String(c.num).padStart(2, "0")}</span>
        </div>
        <p className="mt-2 text-sm italic leading-relaxed text-neutral-400">&ldquo;{c.claim}&rdquo;</p>
        <p className="mt-3 rounded-lg border border-el/15 bg-el/5 p-3 text-sm font-medium leading-relaxed text-neutral-100">
          {c.headline}
        </p>
        <details className="mt-3 text-sm text-neutral-300">
          <summary className="cursor-pointer list-none font-semibold text-neutral-400 transition-colors hover:text-neutral-100">
            How it could have failed
          </summary>
          <p className="mt-2 leading-relaxed">{c.detail}</p>
          <p className="mt-2 leading-relaxed">
            <span className="font-semibold text-neutral-100">Falsification criterion:</span> {c.falsification}
          </p>
        </details>
        <div className="mt-auto pt-4">
          <a
            href={`${REPO}/tree/main/${c.repoPath}`}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-el underline-offset-4 hover:underline"
          >
            Code, data &amp; full writeup
            <ArrowRight size={14} weight="bold" aria-hidden />
          </a>
        </div>
      </div>
    </article>
  );
}

export default function Home() {
  const items = claims as Claim[];
  const ordered = [...items.filter((c) => FEATURED.has(c.num)), ...items.filter((c) => !FEATURED.has(c.num))];
  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      {/* asymmetric split hero: copy left, real evidence artifact right */}
      <header className="grid items-center gap-10 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-el/80">Apollo Forensics</p>
          <h1 className="mt-4 text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
            12 hoax claims.
            <br />
            12 falsifiable tests.
            <br />
            <span className="text-el">Zero survived.</span>
          </h1>
          <p className="mt-5 max-w-[46ch] text-base leading-relaxed text-neutral-300">
            Every moon-landing hoax claim testable in software, tested on public data. Each test could have vindicated
            the hoax. None did.
          </p>
          <div className="mt-7">
            <Link
              href="/mission"
              className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-el px-5 py-2.5 text-sm font-bold text-neutral-950 transition-transform hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]"
            >
              <MoonStars size={16} weight="fill" aria-hidden />
              Replay Apollo 11 on the real computer
            </Link>
          </div>
          <dl className="mt-9 grid max-w-md grid-cols-3 gap-6 border-t border-neutral-800 pt-6">
            {[
              ["5.0σ", "radio echo detection"],
              ["36/36", "flight-code checksums"],
              ["0.2°", "terrain match, JAXA DEM"],
            ].map(([n, l]) => (
              <div key={l}>
                <dt className="sr-only">{l}</dt>
                <dd className="font-mono text-xl font-bold text-neutral-50">{n}</dd>
                <dd className="mt-1 text-xs leading-snug text-neutral-500">{l}</dd>
              </div>
            ))}
          </dl>
        </div>
        <figure className="lg:col-span-5">
          <div className="overflow-hidden rounded-xl border border-neutral-800">
            {/* animated blink comparison from claim 4: real evidence, not decoration */}
            <Image
              src="/figures/04-backdrop-parallax.gif"
              alt="Two Apollo 15 photographs aligned and alternating: the same distant mountains with the Lunar Module present in one frame and absent in the other."
              width={800}
              height={533}
              unoptimized
              priority
              className="w-full"
            />
          </div>
          <figcaption className="mt-2 text-xs leading-relaxed text-neutral-500">
            The famous &ldquo;identical background&rdquo; pair, aligned and blinking. The mountain is real terrain
            measured at 10-34 km away in <a className="underline hover:text-neutral-300" href="#claim-4">claim #4</a>.
          </figcaption>
        </figure>
      </header>

      {/* the evidence grid: featured pair first, then the rest */}
      <section className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3" aria-label="The twelve claims">
        {ordered.map((c, i) => (
          <Reveal key={c.num} delay={Math.min(i * 0.04, 0.3)} className={FEATURED.has(c.num) ? "sm:col-span-2 flex" : "flex"}>
            <ClaimCard c={c} featured={FEATURED.has(c.num)} />
          </Reveal>
        ))}
      </section>

      {/* the audible one */}
      <section className="mx-auto mt-20 max-w-3xl">
        <Reveal>
          <div className="rounded-xl border border-el/20 bg-el/5 p-6 sm:p-8">
            <div className="flex items-center gap-2 text-el">
              <Waveform size={20} aria-hidden />
              <h2 className="text-xl font-bold text-neutral-50">Hear the Moon answer back</h2>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-neutral-300">
              From claim #22: CapCom&apos;s voice, leaking through the astronauts&apos; headsets, returns to Houston{" "}
              <span className="font-semibold text-el">2.644 ± 0.035 seconds</span> after he speaks. That is the
              Earth-Moon round trip at the speed of light, measured across 43 transmissions in the EVA tape.
            </p>
            <audio controls preload="none" src="/figures/echo_example.wav" className="mt-5 w-full" aria-label="Eleven-second mission audio sample: CapCom speaks, and his voice returns from the Moon 2.6 seconds later" />
          </div>
        </Reveal>
      </section>

      <footer className="mt-20 border-t border-neutral-800 py-8 text-center text-xs leading-relaxed text-neutral-500">
        <p>
          Built with Claude Code. Methodology from &ldquo;The Moon Landing Verification Playbook.&rdquo; Everything
          reproducible from{" "}
          <a className="underline hover:text-neutral-300" href={REPO}>
            the public repo
          </a>
          .
        </p>
      </footer>
    </main>
  );
}
