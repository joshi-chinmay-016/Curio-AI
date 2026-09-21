"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, MoreVertical } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";

export interface GapReportHeaderProps {
  topicName: string;
  sessionId: string;
}

export function GapReportHeader({ topicName, sessionId }: GapReportHeaderProps) {
  return (
    <header className="w-full bg-white border-b border-fog px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Link
          href={`/session/${sessionId}`}
          className="inline-flex items-center gap-1.5 font-mono text-xs uppercase font-semibold text-navy/70 hover:text-navy transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>SESSION</span>
        </Link>
        <span className="text-fog">/</span>
        <div>
          <div className="font-mono text-[11px] uppercase tracking-wider text-navy/50 font-bold">
            GAP REPORT
          </div>
          <h1 className="font-heading text-xl md:text-2xl font-bold text-navy leading-tight">
            {topicName}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <KeycapButton
          variant="ghost"
          size="sm"
          disabled
          title="Export feature coming soon"
          className="hidden sm:inline-flex opacity-50"
        >
          EXPORT
        </KeycapButton>
        <KeycapButton
          variant="ghost"
          size="sm"
          disabled
          title="Share feature coming soon"
          className="hidden sm:inline-flex opacity-50"
        >
          SHARE
        </KeycapButton>
        <button
          disabled
          className="p-2 text-navy/40 hover:text-navy transition-colors sm:hidden"
          aria-label="More options"
        >
          <MoreVertical className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
