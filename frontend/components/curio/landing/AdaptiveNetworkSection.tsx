"use client";

import React, { useState } from "react";
import { Check, AlertTriangle, Layers, ArrowRight } from "lucide-react";

export function AdaptiveNetworkSection() {
  const [selectedState, setSelectedState] = useState<"mastered" | "developing" | "gap" | "resolved">("gap");

  const stateDetails = {
    mastered: {
      title: "Mastered Node",
      color: "bg-navy text-white",
      badge: "SOLID NAVY",
      description:
        "Demonstrated deep intuition across definitions, mechanisms, and edge cases. Verified under multiple inquiry angles.",
      visualClass: "bg-navy border-2 border-navy text-white shadow-md",
    },
    developing: {
      title: "Developing Node",
      color: "bg-cobalt text-white",
      badge: "COBALT 75%",
      description:
        "Understands the general premise, but struggles with nuanced state transitions or trade-offs when probed deeply.",
      visualClass: "bg-cobalt/80 border-2 border-cobalt text-white shadow-md",
    },
    gap: {
      title: "Knowledge Gap",
      color: "bg-gap-orange text-white",
      badge: "HATCHED ORANGE",
      description:
        "Critical misconception or missing boundary condition detected. The node pulses orange and triggers targeted intervention.",
      visualClass: "bg-white border-2 border-gap-orange bg-gap-hatch text-gap-orange shadow-md",
    },
    resolved: {
      title: "Resolved Misconception",
      color: "bg-cobalt text-white",
      badge: "COBALT + CHECKMARK",
      description:
        "The gap was addressed during Teacher Mode and validated through targeted verification questions.",
      visualClass: "bg-cobalt border-2 border-cobalt text-white shadow-md",
    },
  };

  return (
    <section className="py-20 border-t border-fog bg-ice/40">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Description */}
          <div className="lg:col-span-6">
            <span className="font-mono text-xs font-bold uppercase tracking-widest text-gap-orange block mb-2">
              DYNAMIC NODE TOPOLOGY
            </span>
            <h2 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-4">
              A Living Map of Your Mind
            </h2>
            <p className="font-sans text-base text-navy/75 leading-relaxed mb-6">
              In Curio, your understanding is mapped as a living 3D network. As you explain concepts, nodes dynamically shift between four cognitive states:
            </p>

            {/* State selector buttons */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              {(["mastered", "developing", "gap", "resolved"] as const).map((key) => {
                const item = stateDetails[key];
                const isSelected = selectedState === key;
                return (
                  <button
                    key={key}
                    onClick={() => setSelectedState(key)}
                    className={`p-3 rounded-[4px] border text-left transition-all duration-150 ${
                      isSelected
                        ? "bg-white border-2 border-navy shadow-[0_3px_0_0_#0F2B4A]"
                        : "bg-white/60 border-fog hover:bg-white text-navy/70"
                    }`}
                  >
                    <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50">
                      {item.badge}
                    </div>
                    <div className="font-heading text-sm font-bold text-navy">
                      {item.title}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="bg-white border border-fog rounded-[6px] p-5 shadow-sm">
              <h4 className="font-heading text-base font-bold text-navy mb-1.5 flex items-center gap-2">
                <span>{stateDetails[selectedState].title}</span>
              </h4>
              <p className="font-sans text-sm text-navy/80 leading-relaxed">
                {stateDetails[selectedState].description}
              </p>
            </div>
          </div>

          {/* Right Column: Node Showcase Card */}
          <div className="lg:col-span-6 flex justify-center">
            <div className="w-full max-w-md bg-white border-2 border-navy rounded-[8px] p-8 shadow-[8px_8px_0_0_#0F2B4A] relative overflow-hidden">
              <div className="font-mono text-[11px] uppercase tracking-wider text-navy/40 font-bold mb-6 flex items-center justify-between">
                <span>NODE INSPECTOR</span>
                <span>STATE: {selectedState.toUpperCase()}</span>
              </div>

              {/* Central Node Graphic */}
              <div className="flex flex-col items-center justify-center py-8">
                <div
                  className={`w-28 h-28 rounded-full flex flex-col items-center justify-center transition-all duration-500 relative ${stateDetails[selectedState].visualClass}`}
                >
                  {selectedState === "resolved" && (
                    <Check className="w-10 h-10 text-white stroke-[3]" />
                  )}
                  {selectedState === "gap" && (
                    <div className="bg-white/90 px-2 py-0.5 rounded-[3px] border border-gap-orange text-gap-orange font-mono text-[11px] font-bold">
                      ⚠ GAP
                    </div>
                  )}
                  {selectedState === "mastered" && (
                    <div className="font-mono text-xs font-bold text-white tracking-widest">
                      100%
                    </div>
                  )}
                  {selectedState === "developing" && (
                    <div className="font-mono text-xs font-bold text-white tracking-widest">
                      70%
                    </div>
                  )}
                </div>

                <div className="font-heading text-lg font-bold text-navy mt-4">
                  {selectedState === "gap" ? "Boundary Conditions" : "Core Mechanism"}
                </div>
                <div className="font-mono text-xs text-navy/60 mt-1">
                  Layer: Edge Cases · Confidence: 85%
                </div>
              </div>

              <div className="border-t border-fog pt-4 flex items-center justify-between text-xs font-mono text-navy/70">
                <span>CONNECTS TO: 3 CONCEPTS</span>
                <span className="font-semibold text-cobalt">4-LAYER MAP →</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
