"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, LayoutDashboard, Mic, BookOpen, Sparkles } from "lucide-react";

interface GapReportHeaderProps {
  topicName: string;
  onBack: () => void;
}

export default function GapReportHeader({
  topicName,
  onBack,
}: GapReportHeaderProps) {
  return (
    <header className="border-b-2 border-navy bg-white px-4 md:px-6 py-3 flex items-center justify-between shrink-0 shadow-sm sticky top-0 z-30">
      <div className="flex items-center gap-3 md:gap-4 min-w-0">
        <button
          onClick={onBack}
          className="flex items-center justify-center w-8 h-8 rounded-[4px] border-2 border-navy bg-white hover:bg-navy hover:text-white text-navy shadow-[2px_2px_0_0_#0F2B4A] transition-all active:translate-y-[2px] active:shadow-none cursor-pointer shrink-0"
          aria-label="Back"
          title="Back to sessions"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-2 min-w-0">
          <span className="font-mono text-[10px] md:text-xs font-bold uppercase tracking-widest text-navy/60 bg-ice px-2 py-0.5 rounded-[3px] border border-navy/20 shrink-0">
            GAP REPORT
          </span>
          <span className="text-navy/30 hidden sm:inline">/</span>
          <h2 className="font-heading text-sm md:text-xl font-bold uppercase tracking-tight text-navy truncate">
            {topicName}
          </h2>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Link
          href="/dashboard"
          className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-semibold uppercase text-navy/70 hover:text-navy hover:bg-ice rounded-[4px] transition-colors"
        >
          <LayoutDashboard className="w-3.5 h-3.5 text-cobalt" />
          <span>DASHBOARD</span>
        </Link>

        <Link
          href="/audio-learning"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-semibold uppercase text-navy/80 hover:text-navy bg-gap-orange/10 border border-gap-orange/30 hover:bg-gap-orange/20 rounded-[4px] transition-colors"
        >
          <Mic className="w-3.5 h-3.5 text-gap-orange" />
          <span className="hidden sm:inline">AUDIO PRACTICE</span>
        </Link>

        <Link
          href="/history"
          className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-semibold uppercase text-navy/70 hover:text-navy hover:bg-ice rounded-[4px] transition-colors"
        >
          <BookOpen className="w-3.5 h-3.5 text-navy/50" />
          <span>HISTORY</span>
        </Link>

        <Link
          href="/topics"
          className="inline-flex items-center gap-1 px-3 py-1.5 bg-navy text-white hover:bg-[#183d66] rounded-[4px] font-mono text-xs font-bold uppercase transition-colors"
        >
          <Sparkles className="w-3 h-3 text-gap-orange" />
          <span>NEW</span>
        </Link>
      </div>
    </header>
  );
}
