"use client";

import React from "react";
import Link from "next/link";
import { SessionSummary } from "@/types/history";
import { KeycapButton } from "@/components/curio/KeycapButton";

export interface SessionCardProps {
  session: SessionSummary;
}

export function SessionCard({ session }: SessionCardProps) {
  const isInProgress = session.status === "IN_PROGRESS";
  const hasGaps = session.unresolvedGaps > 0;

  const dateStr = new Date(session.createdAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div
      className={`bg-white rounded-[6px] p-5 shadow-sm transition-all duration-200 hover:shadow-md border border-fog flex flex-col justify-between ${
        isInProgress ? "border-l-[3px] border-l-cobalt" : ""
      } ${hasGaps ? "border-b-[2px] border-b-gap-orange" : ""}`}
    >
      <div>
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-heading text-lg font-bold text-navy">
            {session.topicName}
          </h3>
          <span className="font-mono text-xs text-navy/50 whitespace-nowrap">
            {dateStr}
          </span>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-navy/75 mb-3 flex-wrap">
          <span className="font-semibold text-navy">{session.masteryLevel}</span>
          <span className="text-fog">·</span>
          <span className="font-semibold text-cobalt">{session.understandingScore}/100</span>
          <span className="text-fog">·</span>
          <span>{session.turnCount} turns</span>
          <span className="text-fog">·</span>
          <span>{session.durationMinutes} min</span>
        </div>

        <div className="py-2.5 my-2 border-y border-fog/60 font-sans text-xs text-navy/80 flex items-center justify-between">
          <span>
            {session.unresolvedGaps > 0 ? (
              <span className="text-gap-orange font-semibold">
                {session.unresolvedGaps} unresolved gap{session.unresolvedGaps === 1 ? "" : "s"}
              </span>
            ) : (
              <span className="text-navy/60">No unresolved gaps</span>
            )}
          </span>
          <span className="text-fog">·</span>
          <span>
            {session.resolvedMisconceptions} misconception{session.resolvedMisconceptions === 1 ? "" : "s"} resolved
          </span>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3 mt-4">
        {isInProgress ? (
          <Link href={`/session/${session.sessionId}`}>
            <KeycapButton variant="cobalt" size="sm">
              RESUME →
            </KeycapButton>
          </Link>
        ) : (
          <>
            <Link href={`/session/${session.sessionId}/report`}>
              <KeycapButton variant="default" size="sm">
                VIEW REPORT
              </KeycapButton>
            </Link>
            {hasGaps && (
              <Link href={`/session/${session.sessionId}/report`}>
                <KeycapButton variant="gap" size="sm">
                  PRACTICE GAPS
                </KeycapButton>
              </Link>
            )}
          </>
        )}
      </div>
    </div>
  );
}
