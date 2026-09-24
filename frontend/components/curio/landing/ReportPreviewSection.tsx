"use client";

import React from "react";
import Link from "next/link";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { HeroIsometricWidget } from "@/components/curio/HeroIsometricWidget";

export function ReportPreviewSection() {
  return (
    <section className="py-20 border-t border-fog bg-ice/30">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-cobalt block mb-2">
            POST-SESSION SYNTHESIS
          </span>
          <h2 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-4">
            The Isometric Gap Report
          </h2>
          <p className="font-sans text-base text-navy/70 leading-relaxed">
            When your session completes, Curio compiles an architectural breakdown of your understanding across 4 isometric layers: Definition, Mechanism, Application, and Edge Cases.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Column: Metric Cards */}
          <div className="lg:col-span-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white border border-fog rounded-[6px] p-5 shadow-sm">
                <span className="font-mono text-[10px] uppercase font-bold text-navy/50 block mb-1">
                  UNDERSTANDING
                </span>
                <span className="font-heading text-3xl font-bold text-cobalt">
                  88/100
                </span>
              </div>
              <div className="bg-white border border-fog rounded-[6px] p-5 shadow-sm">
                <span className="font-mono text-[10px] uppercase font-bold text-navy/50 block mb-1">
                  MASTERY LEVEL
                </span>
                <span className="font-heading text-3xl font-bold text-navy">
                  Proficient
                </span>
              </div>
            </div>

            <div className="bg-white border-2 border-gap-orange rounded-[6px] p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs uppercase font-bold text-gap-orange">
                  IDENTIFIED GAPS (2)
                </span>
                <span className="font-mono text-[10px] bg-gap-orange text-white px-2 py-0.5 rounded-[2px] font-bold">
                  HIGH PRIORITY
                </span>
              </div>
              <ul className="space-y-1.5 font-sans text-xs text-navy/80">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-gap-orange shrink-0" />
                  <span>Boundary Conditions (low &lt;= high vs low &lt; high)</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-gap-orange shrink-0" />
                  <span>Single-element array edge case handling</span>
                </li>
              </ul>
            </div>

            <div className="bg-white border border-fog rounded-[6px] p-5 shadow-sm">
              <span className="font-mono text-xs uppercase font-bold text-navy/50 block mb-2">
                DELIBERATE ROADMAP
              </span>
              <p className="font-sans text-xs text-navy/80 leading-relaxed">
                1. Trace 1-element arrays with guarded conditions.<br />
                2. Practice midpoint arithmetic overflow guards.<br />
                3. Progress to lower-bound and answer-space binary search.
              </p>
            </div>
          </div>

          {/* Right Column: Mini Isometric Widget Stack */}
          <div className="lg:col-span-6 flex flex-col items-center justify-center">
            <HeroIsometricWidget />
            <Link href="/topics" className="mt-4">
              <KeycapButton variant="navy" size="md">
                EXPERIENCE THE GAP REPORT →
              </KeycapButton>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
