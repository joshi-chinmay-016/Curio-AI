"use client";

import React, { useState } from "react";
import { AlertTriangle, Check, ArrowRight, RefreshCw } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";

export function TeacherModeDemo() {
  const [demoStep, setDemoStep] = useState<0 | 1 | 2 | 3>(0);

  const steps = [
    {
      title: "1. Gap Detected",
      badge: "TRIGGER: GAP FOUND",
      badgeColor: "bg-gap-orange text-white",
      curioText:
        "I noticed an assumption: you said a 1-element array [5] terminates because low and high are both 0. But under while (low < high), 0 < 0 is false immediately, so the item is never inspected!",
      actionText: "SWITCH TO TEACHER MODE →",
    },
    {
      title: "2. Focused Teacher Intervention",
      badge: "TEACHER MODE",
      badgeColor: "bg-gap-orange text-white",
      curioText:
        "Let's isolate this single part: In Binary Search, low <= high ensures that when the search space narrows to a single element where low == high, that final element is still checked.",
      actionText: "VERIFY UNDERSTANDING →",
    },
    {
      title: "3. Verification Question",
      badge: "VERIFICATION",
      badgeColor: "bg-cobalt text-white",
      curioText:
        "Verification check: If target is 8 and the array is [8], what are the values of low and high on the first iteration, and why does low <= high evaluate to true?",
      actionText: "SUBMIT ANSWER →",
    },
    {
      title: "4. Return to Student Mode",
      badge: "LOOP RESTORED ✓",
      badgeColor: "bg-navy text-white",
      curioText:
        "✓ Verified! That makes total sense now. Returning to our original question: Now, why do we set high = mid - 1 instead of high = mid when array[mid] > target?",
      actionText: "RESET DEMO ↺",
    },
  ];

  const handleNext = () => {
    if (demoStep === 3) {
      setDemoStep(0);
    } else {
      setDemoStep((prev) => (prev + 1) as any);
    }
  };

  const current = steps[demoStep];

  return (
    <section className="py-20 border-t border-fog bg-white/50">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center max-w-xl mx-auto mb-12">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-cobalt block mb-2">
            INTERACTIVE DEMO
          </span>
          <h2 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-3">
            Teacher Mode in Action
          </h2>
          <p className="font-sans text-base text-navy/70">
            See how Curio isolates a specific misunderstanding, teaches only what's missing, and verifies it.
          </p>
        </div>

        {/* Demo Box */}
        <div className="bg-white border-2 border-navy rounded-[8px] p-6 md:p-8 shadow-[8px_8px_0_0_#0F2B4A] max-w-3xl mx-auto">
          {/* Progress bar */}
          <div className="flex items-center justify-between gap-2 mb-6">
            {steps.map((s, idx) => (
              <div
                key={idx}
                onClick={() => setDemoStep(idx as any)}
                className={`flex-1 h-1.5 rounded-full cursor-pointer transition-colors ${
                  idx <= demoStep ? "bg-navy" : "bg-fog/60"
                }`}
              />
            ))}
          </div>

          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-heading text-lg font-bold text-navy">
              {current.title}
            </h4>
            <span
              className={`font-mono text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-[2px] ${current.badgeColor}`}
            >
              {current.badge}
            </span>
          </div>

          {/* Dialogue Message */}
          <div
            className={`p-5 rounded-[4px] border my-4 font-sans text-sm md:text-base text-navy leading-relaxed transition-all duration-300 ${
              demoStep === 1 || demoStep === 0
                ? "bg-[#FFF8F5] border-l-[4px] border-l-gap-orange border-y border-r border-gap-orange/30"
                : demoStep === 2
                ? "bg-white border-l-[4px] border-l-cobalt border-y border-r border-fog"
                : "bg-white border-l-[4px] border-l-navy border-y border-r border-fog"
            }`}
          >
            <div className="font-mono text-xs font-bold uppercase tracking-wider text-navy/40 mb-2">
              CURIO SAYS:
            </div>
            <p>{current.curioText}</p>
          </div>

          {/* Action Trigger */}
          <div className="flex justify-end mt-6">
            <KeycapButton
              variant={demoStep === 0 || demoStep === 1 ? "gap" : "navy"}
              size="md"
              onClick={handleNext}
            >
              {current.actionText}
            </KeycapButton>
          </div>
        </div>
      </div>
    </section>
  );
}
