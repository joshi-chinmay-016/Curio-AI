"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";

export interface GapCardProps {
  title: string;
  description?: string;
}

export function GapCard({
  title,
  description = "Curio is switching to teacher mode to guide you through this specific gap only.",
}: GapCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="w-full my-4 bg-[#FFF8F5] border border-gap-orange/30 border-l-[4px] border-l-gap-orange rounded-[4px] p-4 shadow-sm"
    >
      <div className="flex items-center gap-2 mb-1 text-gap-orange">
        <AlertTriangle className="w-4 h-4 shrink-0" />
        <span className="font-mono text-xs font-bold uppercase tracking-wider">
          GAP IDENTIFIED
        </span>
      </div>
      <h4 className="font-heading text-base font-bold text-navy mb-1">
        {title}
      </h4>
      <p className="font-sans text-xs md:text-sm text-navy/80">
        {description}
      </p>
    </motion.div>
  );
}
