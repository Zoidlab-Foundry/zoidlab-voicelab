import type { Metadata } from "next";
import "./globals.css";
import VoiceNav from "../components/VoiceNav";
import FoundryAccessGate from "../components/FoundryAccessGate";

export const metadata: Metadata = {
  title: "ZoidLab VoiceLab",
  description: "AI voice lab — design voice agents and test them in real simulated calls.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-bg text-ink">
        <VoiceNav />
        <main className="mx-auto w-full max-w-[1320px] px-5">
          <FoundryAccessGate packageLabel="Foundry Package 11">{children}</FoundryAccessGate>
        </main>
        <footer className="mx-auto mt-20 w-full max-w-[1320px] border-t border-line px-5 py-8 text-[12px] text-faint">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>ZoidLab VoiceLab · Foundry Package 11 · Design voice agents, test them in real simulated calls.</span>
            <span className="flex gap-4"><a href="https://foundry.zoidlab.ai" className="hover:text-dim">Foundry</a><a href="https://zoidlab.ai" className="hover:text-dim">zoidlab.ai</a></span>
          </div>
        </footer>
      </body>
    </html>
  );
}
