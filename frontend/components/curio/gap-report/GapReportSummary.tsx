"use client";

import React from "react";
import { GapReport } from "@/types/gapReport";

export interface GapReportSummaryProps {
  report: GapReport;
}

export function GapReportSummary({ report }: GapReportSummaryProps) {
  const cards = [
    {
      label: "UNDERSTANDING",
      value: `${report.understandingScore}/100`,
      accent: "text-cobalt",
      border: "border-fog",
    },
    {
      label: "MASTERY",
      value: report.masteryLevel,
      accent: "text-navy",
      border: "border-fog",
    },
    {
      label: "KNOWLEDGE GAPS",
      value: `${report.knowledgeGaps}`,
      accent: report.knowledgeGaps > 0 ? "text-gap-orange" : "text-navy",
      border: report.knowledgeGaps > 0 ? "border-gap-orange/50" : "border-fog",
    },
    {
      label: "RESOLVED",
      value: `${report.resolvedMisconceptions} misconception${
        report.resolvedMisconceptions === 1 ? "" : "s"
      }`,
      accent: "text-cobalt",
      border: "border-fog",
    },
  ];

  return (
    <div className="w-full grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 my-6">
      {cards.map((card, idx) => (
        <div
          key={idx}
          className={`bg-white border ${card.border} rounded-[6px] p-4 shadow-sm flex flex-col justify-between`}
        >
          <span className="font-mono text-[10px] md:text-xs font-bold uppercase tracking-wider text-navy/50 mb-1">
            {card.label}
          </span>
          <span
            className={`font-heading text-lg md:text-2xl font-bold tracking-tight ${card.accent}`}
          >
            {card.value}
          </span>
        </div>
      ))}
    </div>
  );
}
