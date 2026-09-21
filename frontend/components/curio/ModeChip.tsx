"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface ModeChipProps {
  mode: "STUDENT" | "TEACHER" | "EVALUATOR" | "LEARNER";
  className?: string;
}

export function ModeChip({ mode, className }: ModeChipProps) {
  if (mode === "STUDENT") {
    return (
      <span
        className={cn(
          "inline-flex items-center px-1.5 py-0.5 rounded-[2px] font-mono text-[10px] font-bold tracking-wider uppercase bg-cobalt text-white",
          className
        )}
      >
        STUDENT
      </span>
    );
  }

  if (mode === "TEACHER") {
    return (
      <span
        className={cn(
          "inline-flex items-center px-1.5 py-0.5 rounded-[2px] font-mono text-[10px] font-bold tracking-wider uppercase bg-gap-orange text-white",
          className
        )}
      >
        TEACHER
      </span>
    );
  }

  if (mode === "EVALUATOR") {
    return (
      <span
        className={cn(
          "inline-flex items-center px-1.5 py-0.5 rounded-[2px] font-mono text-[10px] font-bold tracking-wider uppercase bg-navy text-white",
          className
        )}
      >
        EVALUATOR
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded-[2px] font-mono text-[10px] font-bold tracking-wider uppercase bg-navy/10 text-navy",
        className
      )}
    >
      YOU
    </span>
  );
}
