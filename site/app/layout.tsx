import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Apollo Forensics — 12 hoax claims, 12 falsifiable tests",
  description:
    "Every moon-landing hoax claim that can be tested in software — tested, on public data, with the code in the open. Plus a live replay of the Apollo 11 guidance computer.",
  metadataBase: new URL("https://apollo-forensics.vercel.app"),
  openGraph: {
    title: "Apollo Forensics",
    description: "12 moon-landing hoax claims, 12 falsifiable software tests. A test that can't fail isn't a test.",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
