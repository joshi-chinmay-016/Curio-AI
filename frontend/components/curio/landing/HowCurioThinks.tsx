"use client";

import React from "react";
import { Brain, Sparkles, AlertTriangle, CheckCircle2 } from "lucide-react";
import { FeynmanLoop3D } from "./FeynmanLoop3D";

export function HowCurioThinks() {
  const steps = [
    {
      number: "01",
      mode: "STUDENT MODE",
      title: "You Teach Curio",
      description:
        "You explain a concept in your own natural language. Curio acts as a curious novice, listening carefully without judging.",
      badge: "Inquiry",
      badgeColor: "bg-cobalt text-white",
      icon: Brain,
    },
    {
      number: "02",
      mode: "ANALYSIS",
      title: "Gap Detection",
      description:
        "Curio's evaluator analyzes your explanation against cognitive knowledge graphs, probing edge cases, invariants, and hidden assumptions.",
      badge: "Evaluation",
      badgeColor: "bg-navy text-white",
      icon: Sparkles,
    },
    {
      number: "03",
      mode: "TEACHER MODE",
      title: "Targeted Intervention",
      description:
        "When an exact gap is identified, Curio temporarily shifts to Teacher Mode. It isolates that single sub-concept without overwhelming you.",
      badge: "Gap Flagged",
      badgeColor: "bg-gap-orange text-white",
      icon: AlertTriangle,
    },
    {
      number: "04",
      mode: "VERIFICATION",
      title: "Understanding Verified",
      description:
        "Curio poses a targeted verification question. When you resolve the gap, Curio stamps it verified and updates your knowledge score.",
      badge: "Verified ✓",
      badgeColor: "bg-cobalt text-white",
      icon: CheckCircle2,
    },
    {
      number: "05",
      mode: "STUDENT MODE",
      title: "Return to Inquiry",
      description:
        "Curio seamlessly returns to Student Mode, continuing the original interrupted question with your newly solidified foundation.",
      badge: "Loop Complete",
      badgeColor: "bg-navy text-white",
      icon: Brain,
    },
  ];

  return <FeynmanLoop3D steps={steps} />;
}
