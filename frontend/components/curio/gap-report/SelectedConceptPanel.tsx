"use client";

import React from "react";
import { Check, X, Layers, AlertCircle } from "lucide-react";
import { ConceptCell, Gap, GapReport } from "@/types/gapReport";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { GapActionButtons } from "./GapActionButtons";

export interface SelectedConceptPanelProps {
  concept: ConceptCell | null;
  report: GapReport;
  activeTab: "overview" | "gap_details";
  onTabChange: (tab: "overview" | "gap_details") => void;
  onSelectRelatedConcept: (conceptId: string) => void;
  onViewEvidence: (gap: Gap) => void;
  onPracticeGap: (gapId: string) => Promise<void>;
  onSaveForLater: (gapId: string) => Promise<void>;
  onMarkForReview: (gapId: string) => Promise<void>;
}

export function SelectedConceptPanel({
  concept,
  report,
  activeTab,
  onTabChange,
  onSelectRelatedConcept,
  onViewEvidence,
  onPracticeGap,
  onSaveForLater,
  onMarkForReview,
}: SelectedConceptPanelProps) {
  if (!concept) {
    return (
      <div className="w-full h-full min-h-[380px] bg-white border border-fog rounded-[6px] p-8 flex flex-col items-center justify-center text-center shadow-sm">
        <Layers className="w-10 h-10 text-navy/30 mb-3" />
        <h4 className="font-heading text-base font-bold text-navy mb-1">
          Concept Inspector
        </h4>
        <p className="font-sans text-sm text-navy/60 max-w-xs">
          Select any cell in the isometric map to inspect your understanding, detected gaps, and evidence.
        </p>
      </div>
    );
  }

  const isGapOrMisconception =
    concept.status === "GAP" || concept.status === "MISCONCEPTION";

  // Find matching gap if any
  const matchedGap = report.gaps.find(
    (g) =>
      g.conceptId === concept.id ||
      g.title.toLowerCase().includes(concept.name.toLowerCase())
  );

  const getStatusBadge = (status: ConceptCell["status"]) => {
    switch (status) {
      case "STRONG":
        return "bg-navy text-white";
      case "DEVELOPING":
        return "bg-cobalt text-white";
      case "GAP":
        return "bg-gap-orange text-white";
      case "MISCONCEPTION":
        return "bg-[#A82485] text-white";
      case "RESOLVED":
        return "bg-cobalt text-white";
      case "UNTESTED":
      default:
        return "bg-fog text-navy";
    }
  };

  return (
    <div className="w-full bg-white border border-fog rounded-[6px] shadow-sm flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-fog bg-white">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50 block mb-1">
              {concept.layer.replace("_", " ")}
            </span>
            <h3 className="font-heading text-lg md:text-xl font-bold text-navy leading-tight">
              {concept.name}
            </h3>
          </div>
          <span
            className={`font-mono text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-[3px] shrink-0 ${getStatusBadge(
              concept.status
            )}`}
          >
            {concept.status}
          </span>
        </div>

        {/* Tabs if gap exists */}
        {isGapOrMisconception && (
          <div className="flex items-center gap-4 mt-4 border-b border-fog -mb-5">
            <button
              onClick={() => onTabChange("overview")}
              className={`pb-2.5 font-mono text-xs font-semibold uppercase tracking-wider border-b-2 transition-colors ${
                activeTab === "overview"
                  ? "border-navy text-navy"
                  : "border-transparent text-navy/50 hover:text-navy"
              }`}
            >
              OVERVIEW
            </button>
            <button
              onClick={() => onTabChange("gap_details")}
              className={`pb-2.5 font-mono text-xs font-semibold uppercase tracking-wider border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === "gap_details"
                  ? "border-gap-orange text-gap-orange font-bold"
                  : "border-transparent text-navy/50 hover:text-navy"
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5" />
              GAP DETAILS
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-5 flex-1 overflow-y-auto space-y-5">
        {activeTab === "overview" || !isGapOrMisconception ? (
          <>
            {/* Score Bars */}
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-navy/70 uppercase">Understanding Score</span>
                  <span className="font-bold text-cobalt">{concept.score}%</span>
                </div>
                <div className="w-full h-2 bg-ice rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cobalt transition-all duration-500"
                    style={{ width: `${concept.score}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-navy/70 uppercase">Confidence</span>
                  <span className="font-bold text-navy">{concept.confidence}%</span>
                </div>
                <div className="w-full h-2 bg-ice rounded-full overflow-hidden">
                  <div
                    className="h-full bg-navy transition-all duration-500"
                    style={{ width: `${concept.confidence}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Description */}
            {concept.description && (
              <div>
                <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50 block mb-1">
                  ANALYSIS
                </span>
                <p className="font-sans text-sm text-navy/80 leading-relaxed bg-ice/50 p-3 rounded-[4px] border border-fog/60">
                  {concept.description}
                </p>
              </div>
            )}

            {/* Related Concepts */}
            {concept.relatedConceptIds && concept.relatedConceptIds.length > 0 && (
              <div>
                <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50 block mb-1.5">
                  RELATED CONCEPTS
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {concept.relatedConceptIds.map((relId) => {
                    const related = report.concepts.find((c) => c.id === relId);
                    return (
                      <button
                        key={relId}
                        onClick={() => onSelectRelatedConcept(relId)}
                        className="font-mono text-xs px-2.5 py-1 rounded-[3px] bg-ice hover:bg-fog/60 text-navy border border-fog transition-colors uppercase"
                      >
                        {related ? related.name : relId} →
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        ) : (
          /* GAP DETAILS TAB */
          <div className="space-y-4">
            {matchedGap ? (
              <>
                <div>
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-gap-orange block mb-1">
                    WHY THIS IS A GAP
                  </span>
                  <p className="font-sans text-sm text-navy/80 leading-relaxed bg-[#FFF8F5] p-3 rounded-[4px] border border-gap-orange/20">
                    {matchedGap.whyDetected}
                  </p>
                </div>

                {/* Evidence Section */}
                {matchedGap.evidence && matchedGap.evidence.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50">
                        EVIDENCE ({matchedGap.evidence.length} TURNS)
                      </span>
                    </div>
                    <KeycapButton
                      variant="gap"
                      size="sm"
                      onClick={() => onViewEvidence(matchedGap)}
                      className="w-full text-xs"
                    >
                      [VIEW EVIDENCE ▼]
                    </KeycapButton>
                  </div>
                )}

                {/* Intervention & Verification Status */}
                <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                  <div className="p-2.5 bg-ice rounded-[4px] border border-fog">
                    <span className="text-navy/50 uppercase block text-[10px]">
                      TEACHER INTERVENTION
                    </span>
                    <span className="font-bold flex items-center gap-1 mt-1 text-navy">
                      {matchedGap.teacherInterventionAttempted ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-cobalt" /> Attempted
                        </>
                      ) : (
                        <>
                          <X className="w-3.5 h-3.5 text-navy/40" /> Not attempted
                        </>
                      )}
                    </span>
                  </div>

                  <div className="p-2.5 bg-ice rounded-[4px] border border-fog">
                    <span className="text-navy/50 uppercase block text-[10px]">
                      VERIFICATION
                    </span>
                    <span className="font-bold flex items-center gap-1 mt-1 text-navy">
                      {matchedGap.verificationSuccess ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-cobalt" /> Successful
                        </>
                      ) : (
                        <>
                          <X className="w-3.5 h-3.5 text-gap-orange" /> Not demonstrated
                        </>
                      )}
                    </span>
                  </div>
                </div>

                {/* Recommended Next Step */}
                {matchedGap.recommendedAction && (
                  <div>
                    <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50 block mb-1">
                      RECOMMENDED NEXT STEP
                    </span>
                    <p className="font-sans text-xs text-navy/80 leading-relaxed">
                      {matchedGap.recommendedAction}
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="pt-2 border-t border-fog">
                  <GapActionButtons
                    gapId={matchedGap.id}
                    onPracticeGap={onPracticeGap}
                    onSaveForLater={onSaveForLater}
                    onMarkForReview={onMarkForReview}
                  />
                </div>
              </>
            ) : (
              <p className="font-sans text-sm text-navy/60">
                No specific gap report data available for this concept.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
