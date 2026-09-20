"use client";

import { motion, AnimatePresence } from "framer-motion";
import { EvidenceItem } from "@/types/gapReport";
import { X, AlertTriangle } from "lucide-react";
import { KeycapButton } from "@/components/ui/KeycapButton";

interface EvidenceViewerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  evidence: EvidenceItem[];
  conceptName: string;
}

export default function EvidenceViewer({
  open,
  onOpenChange,
  evidence,
  conceptName,
}: EvidenceViewerProps) {
  if (!open) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Navy Backdrop at 50% */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => onOpenChange(false)}
          className="fixed inset-0 bg-navy/50"
        />

        {/* Modal Container: 680px max, 2px solid navy border, 8px 8px 0 0 hard shadow */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="relative z-10 w-full max-w-[680px] max-h-[85vh] bg-white border-2 border-navy shadow-[8px_8px_0_0_#0F2B4A] flex flex-col overflow-hidden text-navy"
        >
          {/* Header */}
          <div className="border-b-2 border-navy p-5 flex items-center justify-between bg-ice/30 shrink-0">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-wider text-navy/60">
                DIAGNOSTIC EVIDENCE TIMELINE
              </p>
              <h3 className="font-sora text-xl font-bold uppercase tracking-tight text-navy mt-0.5">
                {conceptName}
              </h3>
            </div>
            <button
              onClick={() => onOpenChange(false)}
              className="p-1.5 text-navy hover:text-gap-orange transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Timeline Cards */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {evidence.length === 0 ? (
              <p className="font-mono text-xs text-navy/60 text-center py-8">
                NO EVIDENCE ITEMS RECORDED FOR THIS CONCEPT.
              </p>
            ) : (
              evidence.map((item, idx) => {
                const isMisconception = item.detectionType === "misconception";
                const isGap = item.detectionType === "gap";

                return (
                  <div key={idx} className="space-y-2">
                    {/* Turn Header */}
                    <div className="flex items-center justify-between font-mono text-xs font-bold text-navy/70 uppercase">
                      <span>Turn {item.turn}</span>
                      <span>{item.timestamp}</span>
                    </div>

                    {/* Evidence Box */}
                    <div className="border-2 border-navy bg-white shadow-[3px_3px_0_0_#0F2B4A] divide-y-2 divide-navy">
                      {/* Curio Asked */}
                      {item.curioAsked && (
                        <div className="p-3.5 bg-ice/40">
                          <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/60 mb-1">
                            CURIO ASKED
                          </p>
                          <p className="font-mono text-xs text-navy font-medium leading-relaxed">
                            "{item.curioAsked}"
                          </p>
                        </div>
                      )}

                      {/* Your Answer */}
                      {item.learnerAnswered && (
                        <div className="p-3.5 bg-white">
                          <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/60 mb-1">
                            YOUR ANSWER
                          </p>
                          <p className="font-mono text-xs text-navy font-semibold leading-relaxed">
                            "{item.learnerAnswered}"
                          </p>
                        </div>
                      )}

                      {/* Detection Result */}
                      <div
                        className={`p-3.5 ${
                          isMisconception || isGap
                            ? "bg-gap-orange/10 text-gap-orange"
                            : "bg-cobalt/10 text-cobalt"
                        }`}
                      >
                        <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase tracking-wider mb-1">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          <span>
                            CURIO DETECTED: {item.detectionType.toUpperCase()}
                          </span>
                        </div>
                        <p className="font-sans text-xs text-navy/90 leading-relaxed font-medium">
                          {item.explanation}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="border-t-2 border-navy p-4 bg-ice/30 flex justify-end shrink-0">
            <KeycapButton size="sm" onClick={() => onOpenChange(false)}>
              CLOSE TIMELINE
            </KeycapButton>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
