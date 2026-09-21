"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, User, Bell, Shield, Sliders } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Header */}
      <header className="w-full bg-white border-b border-fog px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 font-mono text-xs uppercase font-semibold text-navy/70 hover:text-navy transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>HOME</span>
            </Link>
            <span className="text-fog">/</span>
            <span className="font-mono text-xs uppercase tracking-wider text-navy/50 font-bold">
              CURIO / SETTINGS
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10">
        <div className="mb-8">
          <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-navy tracking-tight mb-2">
            Preferences & Settings
          </h1>
          <p className="font-sans text-sm text-navy/70">
            Manage your learning laboratory configuration and preferences.
          </p>
        </div>

        <div className="space-y-6">
          {/* Profile card */}
          <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <User className="w-5 h-5 text-cobalt" />
              <h3 className="font-heading text-base font-bold text-navy">
                Learner Profile
              </h3>
            </div>
            <p className="font-sans text-sm text-navy/75 mb-4">
              Curio adapts its inquiry style and difficulty based on your explanations and responses.
            </p>
            <div className="flex items-center justify-between py-2 border-t border-fog/60 font-mono text-xs">
              <span className="text-navy/60">LEARNING MODE</span>
              <span className="font-semibold text-navy">Adaptive Feynman (Default)</span>
            </div>
          </div>

          {/* Inquiry Settings */}
          <div className="bg-white border border-fog rounded-[6px] p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Sliders className="w-5 h-5 text-gap-orange" />
              <h3 className="font-heading text-base font-bold text-navy">
                Inquiry Sensitivity
              </h3>
            </div>
            <p className="font-sans text-sm text-navy/75 mb-4">
              Adjust how rigorously Curio probes edge cases and boundary conditions before validating a concept.
            </p>
            <div className="flex items-center justify-between py-2 border-t border-fog/60 font-mono text-xs">
              <span className="text-navy/60">PROBING DEPTH</span>
              <span className="font-semibold text-navy">Rigorous (4 Layers)</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
