"use client";

import { motion } from "framer-motion";
import { GapReport } from "@/types/gapReport";
import { Brain, Target, AlertTriangle, CheckCircle2 } from "lucide-react";

interface GapReportSummaryProps {
  report: GapReport;
}

export default function GapReportSummary({ report }: GapReportSummaryProps) {
  const cards = [
    {
      label: "UNDERSTANDING",
      value: `${report.understandingScore} / 100`,
      icon: <Brain className="h-4 w-4 text-cobalt" />,
      accent: "text-cobalt",
    },
    {
      label: "MASTERY",
      value: report.masteryLevel,
      icon: <Target className="h-4 w-4 text-navy" />,
      accent: "text-navy",
    },
    {
      label: "KNOWLEDGE GAPS",
      value: `${report.knowledgeGaps}`,
      icon: <AlertTriangle className="h-4 w-4 text-gap-orange" />,
      accent: "text-gap-orange",
    },
    {
      label: "MISCONCEPTIONS",
      value: `${report.resolvedMisconceptions} RESOLVED`,
      icon: <CheckCircle2 className="h-4 w-4 text-cobalt" />,
      accent: "text-navy",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4 shrink-0">
      {cards.map((card, idx) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: idx * 0.08 }}
          className="bg-white border border-navy/20 rounded-[6px] p-3.5 shadow-sm hover:border-cobalt hover:-translate-y-[2px] transition-all duration-150 select-none group"
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-[11px] font-semibold text-navy/60 uppercase tracking-wider">
              {card.label}
            </span>
            <div className="opacity-75 group-hover:opacity-100 transition-opacity">
              {card.icon}
            </div>
          </div>
          <div className={`font-sora text-xl md:text-2xl font-bold tracking-tight ${card.accent}`}>
            {card.value}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
