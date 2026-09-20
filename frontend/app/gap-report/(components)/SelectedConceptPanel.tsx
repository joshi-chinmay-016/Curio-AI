"use client";

import { useState } from "react";
import { ConceptCell, Gap } from "@/types/gapReport";
import { KeycapButton } from "@/components/ui/KeycapButton";
import { AlertTriangle, CheckCircle2, Eye, HelpCircle } from "lucide-react";
import GapActionButtons from "./GapActionButtons";
import EvidenceViewer from "./EvidenceViewer";

interface SelectedConceptPanelProps {
  concept: ConceptCell | undefined;
  gap: Gap | undefined;
  onSelectRelated: (conceptId: string) => void;
}

export default function SelectedConceptPanel({
  concept,
  gap,
  onSelectRelated,
}: SelectedConceptPanelProps) {
  const [showEvidence, setShowEvidence] = useState(false);

  // Empty State
  if (!concept) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center bg-white border border-navy/20 rounded-xl shadow-sm text-navy">
        <div className="w-12 h-12 rounded-[6px] border-2 border-navy flex items-center justify-center mb-3 bg-ice text-navy shadow-[2px_2px_0_0_#0F2B4A]">
          <HelpCircle className="h-6 w-6 text-navy" />
        </div>
        <h4 className="font-sora font-bold text-base uppercase tracking-tight text-navy mb-1">
          CONCEPT EXPLORER
        </h4>
        <p className="font-sans text-xs text-navy/70 max-w-xs leading-relaxed">
          Select any cell in the isometric map to inspect your understanding, examine diagnostic evidence, and practice gaps.
        </p>
      </div>
    );
  }

  const isGap = concept.status === "GAP" || concept.status === "MISCONCEPTION" || Boolean(gap);
  const isResolved = concept.status === "RESOLVED";
  const isStrong = concept.status === "STRONG";
  const isDeveloping = concept.status === "DEVELOPING";
  const isUntested = concept.status === "UNTESTED";

  return (
    <div className="h-full flex flex-col bg-white border border-navy/20 rounded-xl shadow-sm overflow-hidden text-navy">
      {/* Header */}
      <div className="p-4 border-b-2 border-navy bg-ice/40 shrink-0">
        <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/60">
          LAYER: {concept.layer.replace("_", " ")}
        </p>
        <h3 className="font-sora text-lg font-bold uppercase tracking-tight text-navy mt-0.5 leading-snug">
          {concept.name}
        </h3>

        {/* Status Badge */}
        <div className="mt-2 flex items-center gap-2">
          {isGap && (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] font-bold uppercase px-2 py-0.5 rounded-[4px] bg-gap-orange/15 text-gap-orange border border-gap-orange/40">
              <AlertTriangle className="h-3 w-3" />
              UNRESOLVED GAP {gap?.severity ? `[${gap.severity} SEVERITY]` : ""}
            </span>
          )}
          {isResolved && (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] font-bold uppercase px-2 py-0.5 rounded-[4px] bg-cobalt/15 text-cobalt border border-cobalt/40">
              <CheckCircle2 className="h-3 w-3" />
              RESOLVED MISCONCEPTION
            </span>
          )}
          {isStrong && (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] font-bold uppercase px-2 py-0.5 rounded-[4px] bg-navy/10 text-navy border border-navy/30">
              <CheckCircle2 className="h-3 w-3 text-cobalt" />
              STRONG MASTERY
            </span>
          )}
          {isDeveloping && (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] font-bold uppercase px-2 py-0.5 rounded-[4px] bg-ice text-navy/80 border border-navy/20">
              DEVELOPING CONCEPT
            </span>
          )}
          {isUntested && (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] font-bold uppercase px-2 py-0.5 rounded-[4px] bg-ice text-navy/60 border border-navy/20">
              UNTESTED TOPIC
            </span>
          )}
        </div>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs font-sans">
        {/* Progress Bars */}
        <div className="space-y-3 p-3.5 bg-ice/30 rounded-[6px] border border-navy/15">
          {/* Understanding Score */}
          <div className="space-y-1">
            <div className="flex justify-between items-center font-mono text-[11px] font-bold uppercase">
              <span className="text-navy/70">UNDERSTANDING</span>
              <span className="text-navy font-extrabold">{concept.score}%</span>
            </div>
            <div className="w-full bg-white border border-navy/20 h-2.5 rounded-[3px] overflow-hidden p-[1px]">
              <div
                className={`h-full rounded-[2px] transition-all duration-300 ${
                  isGap ? "bg-gap-orange" : isStrong ? "bg-navy" : "bg-cobalt"
                }`}
                style={{ width: `${concept.score}%` }}
              />
            </div>
          </div>

          {/* Curio Confidence */}
          <div className="space-y-1">
            <div className="flex justify-between items-center font-mono text-[11px] font-bold uppercase">
              <span className="text-navy/70">CONFIDENCE (CURIO)</span>
              <span className="text-navy font-extrabold">{concept.confidence}%</span>
            </div>
            <div className="w-full bg-white border border-navy/20 h-2.5 rounded-[3px] overflow-hidden p-[1px]">
              <div
                className="h-full bg-cobalt rounded-[2px] transition-all duration-300"
                style={{ width: `${concept.confidence}%` }}
              />
            </div>
          </div>
        </div>

        {/* Concept Description */}
        {concept.description && (
          <div className="space-y-1">
            <h5 className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/60">
              ABOUT THIS CONCEPT
            </h5>
            <p className="text-navy/90 leading-relaxed font-medium">
              {concept.description}
            </p>
          </div>
        )}

        {/* GAP Specific Sections */}
        {gap && (
          <>
            {/* Why This Is a Gap */}
            <div className="space-y-1 pt-1 border-t border-navy/15">
              <h5 className="font-mono text-[10px] font-bold uppercase tracking-wider text-gap-orange">
                WHY THIS IS A GAP
              </h5>
              <p className="text-navy/90 leading-relaxed font-medium">
                {gap.whyDetected}
              </p>
            </div>

            {/* Evidence Preview & Button */}
            <div className="space-y-2 pt-1 border-t border-navy/15">
              <div className="flex items-center justify-between">
                <h5 className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/60">
                  EVIDENCE ({gap.evidence.length} TURNS)
                </h5>
              </div>

              <div className="space-y-1.5 font-mono text-[11px] text-navy/80 bg-ice/40 p-2.5 rounded-[4px] border border-navy/15">
                {gap.evidence.slice(0, 2).map((ev, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span>Turn {ev.turn}</span>
                    <span className="text-gap-orange font-bold uppercase">
                      · {ev.detectionType}
                    </span>
                  </div>
                ))}
              </div>

              <KeycapButton
                size="sm"
                variant="default"
                className="w-full justify-center"
                onClick={() => setShowEvidence(true)}
              >
                <Eye className="h-3 w-3 mr-1 text-cobalt" />
                VIEW EVIDENCE ▼
              </KeycapButton>
            </div>

            {/* Teacher Intervention & Verification */}
            <div className="pt-2 border-t border-navy/15 font-mono text-[11px] space-y-1.5 bg-ice/20 p-2.5 rounded-[4px] border border-navy/10">
              <div className="flex justify-between items-center">
                <span className="text-navy/70 uppercase">TEACHER INTERVENTION</span>
                <span className={gap.teacherInterventionAttempted ? "text-cobalt font-bold" : "text-navy/50"}>
                  {gap.teacherInterventionAttempted ? "✓ ATTEMPTED" : "✗ NOT ATTEMPTED"}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-navy/70 uppercase">VERIFICATION</span>
                <span className={gap.verificationSuccess ? "text-cobalt font-bold" : "text-gap-orange font-bold"}>
                  {gap.verificationSuccess ? "✓ VERIFIED" : "✗ NOT DONE"}
                </span>
              </div>
            </div>

            {/* Next Step */}
            <div className="space-y-1 pt-1 border-t border-navy/15">
              <h5 className="font-mono text-[10px] font-bold uppercase tracking-wider text-cobalt">
                NEXT STEP
              </h5>
              <p className="text-navy/90 leading-relaxed font-medium">
                {gap.recommendedAction}
              </p>
            </div>
          </>
        )}

        {/* Related Concepts */}
        {concept.relatedConceptIds.length > 0 && (
          <div className="space-y-1.5 pt-1 border-t border-navy/15">
            <h5 className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/60">
              RELATED CONCEPTS
            </h5>
            <div className="flex flex-wrap gap-1.5">
              {concept.relatedConceptIds.map((relId) => (
                <button
                  key={relId}
                  onClick={() => onSelectRelated(relId)}
                  className="font-mono text-[10px] uppercase font-semibold px-2 py-1 bg-ice hover:bg-navy hover:text-white text-navy rounded-[4px] border border-navy/20 transition-colors"
                >
                  → {relId.replace(/^(def|mech|app|edge)-/, "").replace(/-/g, " ")}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="pt-2 border-t-2 border-navy">
          <GapActionButtons
            gapId={gap?.id}
            conceptId={concept.id}
            isGap={isGap}
            isResolved={isResolved}
          />
        </div>
      </div>

      {/* Evidence Timeline Modal */}
      {gap && (
        <EvidenceViewer
          open={showEvidence}
          onOpenChange={setShowEvidence}
          evidence={gap.evidence}
          conceptName={concept.name}
        />
      )}
    </div>
  );
}
