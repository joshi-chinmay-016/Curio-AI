"use client";

import React from "react";
import Link from "next/link";
import { PracticeQueueItem } from "@/types/history";
import { KeycapButton } from "@/components/curio/KeycapButton";

export interface PracticeQueueCardProps {
  item: PracticeQueueItem;
}

export function PracticeQueueCard({ item }: PracticeQueueCardProps) {
  const dateStr = new Date(item.savedAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  const getSeverityBadge = (sev: PracticeQueueItem["severity"]) => {
    switch (sev) {
      case "HIGH":
        return "bg-gap-orange text-white";
      case "MEDIUM":
        return "bg-[#E67E22] text-white";
      case "LOW":
      default:
        return "bg-cobalt text-white";
    }
  };

  return (
    <div className="bg-white rounded-[6px] p-5 shadow-sm border border-fog border-l-[3px] border-l-gap-orange flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50">
            {item.topicName}
          </span>
          <span className="text-fog">·</span>
          <span
            className={`font-mono text-[10px] font-bold uppercase px-2 py-0.5 rounded-[2px] ${getSeverityBadge(
              item.severity
            )}`}
          >
            {item.severity} PRIORITY
          </span>
          <span className="text-fog">·</span>
          <span className="font-mono text-[10px] text-navy/40">Saved {dateStr}</span>
        </div>

        <h4 className="font-heading text-base font-bold text-navy">
          {item.conceptName}
        </h4>
      </div>

      <div className="shrink-0 flex items-center justify-end">
        <Link href={`/topics`}>
          <KeycapButton variant="gap" size="sm">
            PRACTICE NOW ▶
          </KeycapButton>
        </Link>
      </div>
    </div>
  );
}
