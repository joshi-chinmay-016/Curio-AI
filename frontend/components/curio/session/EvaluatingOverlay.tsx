"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

export interface EvaluatingOverlayProps {
  turnCount: number;
}

export function EvaluatingOverlay({ turnCount }: EvaluatingOverlayProps) {
  const [step, setStep] = useState(1);

  useEffect(() => {
    const t1 = setTimeout(() => setStep(2), 700);
    const t2 = setTimeout(() => setStep(3), 1500);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/20 backdrop-blur-[1px] p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md bg-white border-2 border-navy rounded-none shadow-[8px_8px_0_0_#0F2B4A] p-8 text-navy"
      >
        <div className="font-mono text-xs uppercase tracking-widest text-cobalt font-bold mb-3 flex items-center gap-2">
          <span className="inline-block animate-spin">◈</span>
          CURIO IS EVALUATING
        </div>

        <div className="space-y-3 font-mono text-sm">
          <div className="flex items-center justify-between text-navy">
            <span>Analyzing {turnCount} turns</span>
            <span className="text-cobalt font-bold">
              {step >= 1 ? "DONE" : "..."}
            </span>
          </div>

          <div
            className={`flex items-center justify-between transition-opacity duration-300 ${
              step >= 2 ? "opacity-100 text-navy" : "opacity-30 text-navy/40"
            }`}
          >
            <span>Mapping knowledge gaps</span>
            <span className="text-gap-orange font-bold">
              {step >= 2 ? (step > 2 ? "DONE" : "...") : ""}
            </span>
          </div>

          <div
            className={`flex items-center justify-between transition-opacity duration-300 ${
              step >= 3 ? "opacity-100 text-navy" : "opacity-30 text-navy/40"
            }`}
          >
            <span>Generating your report</span>
            <span className="text-cobalt font-bold">
              {step >= 3 ? "..." : ""}
            </span>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-fog/60 text-[11px] font-mono text-navy/50 uppercase text-center">
          PREPARING ISOMETRIC KNOWLEDGE MAP
        </div>
      </motion.div>
    </div>
  );
}
