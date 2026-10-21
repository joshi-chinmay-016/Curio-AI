"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowLeft,
  LayoutDashboard,
  Mic,
  BookOpen,
  FileText,
  Share2,
} from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";

export interface GapReportHeaderProps {
  topicName: string;
  sessionId: string;
}

export function GapReportHeader({ topicName, sessionId }: GapReportHeaderProps) {
  return (
    <header className="w-full bg-white border-b border-fog px-4 md:px-6 py-3 flex items-center justify-between shadow-xs sticky top-0 z-30">
      <div className="flex items-center gap-3 md:gap-4 min-w-0">
        <Link
          href={`/session/${sessionId}`}
          className="inline-flex items-center gap-1.5 font-mono text-xs uppercase font-semibold text-navy/70 hover:text-navy transition-colors px-2 py-1 bg-ice/60 border border-fog rounded-[4px] shrink-0"
          title="Back to Session Chat"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">SESSION CHAT</span>
        </Link>
        <span className="text-fog hidden sm:inline">/</span>
        <div className="min-w-0">
          <div className="font-mono text-[10px] uppercase tracking-wider text-navy/50 font-bold truncate">
            GAP REPORT
          </div>
          <h1 className="font-heading text-sm md:text-lg font-bold text-navy leading-tight truncate max-w-[200px] sm:max-w-md">
            {topicName}
          </h1>
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
          title="Practice this topic in voice"
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
          className="inline-block"
        >
          <KeycapButton variant="navy" size="sm" className="text-xs">
            NEW SESSION +
          </KeycapButton>
        </Link>
      </div>
    </header>
  );
}
