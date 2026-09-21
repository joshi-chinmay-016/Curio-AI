"use client";

import React from "react";
import { motion } from "framer-motion";

export interface TeacherModeSeparatorProps {
  type: "activated" | "returning";
}

export function TeacherModeSeparator({ type }: TeacherModeSeparatorProps) {
  const isActivated = type === "activated";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full flex items-center justify-center my-6"
    >
      <div
        className={`px-4 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-widest text-center select-none ${
          isActivated
            ? "border border-dashed border-gap-orange text-gap-orange bg-[#FFF8F5] rounded-[3px]"
            : "text-navy/50 tracking-widest"
        }`}
      >
        {isActivated
          ? "── TEACHER MODE ACTIVATED ──"
          : "── RETURNING TO STUDENT MODE ──"}
      </div>
    </motion.div>
  );
}
