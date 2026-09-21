"use client";

import React, { useState } from "react";
import { ArrowRight, CheckCircle2, AlertTriangle, Sparkles, Brain, ArrowDown } from "lucide-react";

export function HowCurioThinks() {
  const [activeStep, setActiveStep] = useState(0);

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

  return (
    <section className="py-20 border-t border-fog bg-white/40">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-cobalt block mb-2">
            THE 5-STAGE FEYNMAN LOOP
          </span>
          <h2 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-4">
            How Curio Thinks With You
          </h2>
          <p className="font-sans text-base text-navy/70 leading-relaxed">
            Unlike standard chatbots that lecture you, Curio creates a dynamic two-way learning loop that systematically surfaces what you don't know.
          </p>
        </div>

        {/* Step Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isActive = activeStep === idx;
            return (
              <div
                key={step.number}
                onClick={() => setActiveStep(idx)}
                className={`p-5 rounded-[6px] border transition-all duration-200 cursor-pointer flex flex-col justify-between ${
                  isActive
                    ? "bg-white border-2 border-navy shadow-[0_4px_0_0_#0F2B4A]"
                    : "bg-white/80 border-fog hover:border-navy/60 hover:bg-white"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-sm font-bold text-navy/40">
                      {step.number}
                    </span>
                    <span
                      className={`font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-[2px] ${step.badgeColor}`}
                    >
                      {step.badge}
                    </span>
                  </div>

                  <h3 className="font-heading text-base font-bold text-navy mb-2">
                    {step.title}
                  </h3>

                  <p className="font-sans text-xs text-navy/75 leading-relaxed">
                    {step.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-fog/50 flex items-center justify-between font-mono text-[10px] text-navy/50 uppercase">
                  <span>{step.mode}</span>
                  <Icon className="w-3.5 h-3.5 text-navy/60" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
