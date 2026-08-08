"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GithubLogo } from "@phosphor-icons/react";

const LINKS = [
  { href: "/", label: "The evidence" },
  { href: "/mission", label: "Mission replay" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav aria-label="Primary" className="sticky top-0 z-40 border-b border-neutral-800/80 bg-[#0a0a0c]/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
        <Link href="/" className="text-[11px] font-bold uppercase tracking-[0.25em] text-el/90">
          Apollo Forensics
        </Link>
        <div className="ml-auto flex items-center gap-1">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={path === l.href ? "page" : undefined}
              className={`flex h-11 items-center rounded-lg px-3 text-sm font-semibold transition-colors ${
                path === l.href ? "text-el" : "text-neutral-400 hover:text-neutral-100"
              }`}
            >
              {l.label}
            </Link>
          ))}
          <a
            href="https://github.com/theryanbyrd/apollo-forensics"
            className="flex h-11 items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-neutral-400 transition-colors hover:text-neutral-100"
          >
            <GithubLogo size={16} aria-hidden />
            <span className="hidden sm:inline">GitHub</span>
          </a>
        </div>
      </div>
    </nav>
  );
}
