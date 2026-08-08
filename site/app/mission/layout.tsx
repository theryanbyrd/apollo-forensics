import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Mission replay · Apollo Forensics",
  description:
    "Scrub Apollo 11 from liftoff to splashdown and watch what the Apollo Guidance Computer was running at every moment, on a live DSKY.",
};

export default function MissionLayout({ children }: LayoutProps<"/mission">) {
  return children;
}
