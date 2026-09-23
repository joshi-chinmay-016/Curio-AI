"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, BookOpen, Brain, Sparkles } from "lucide-react";
import { CurioNav } from "@/components/curio/CurioNav";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { Hero3DScene } from "@/components/curio/landing/Hero3DScene";
import { HowCurioThinks } from "@/components/curio/landing/HowCurioThinks";
import { LearningParadox3D } from "@/components/curio/landing/LearningParadox3D";
import { TypewriterHeadline } from "@/components/curio/landing/TypewriterHeadline";
import { AdaptiveNetworkSection } from "@/components/curio/landing/AdaptiveNetworkSection";
import { TeacherModeDemo } from "@/components/curio/landing/TeacherModeDemo";
import { ReportPreviewSection } from "@/components/curio/landing/ReportPreviewSection";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { CurioFooter } from "@/components/curio/CurioFooter";

export default function LandingPage() {
  const scrollToHowItWorks = () => {
    document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />
      <CurioNav />

      {/* 1. HERO SECTION */}
      <section className="relative w-full max-w-7xl mx-auto px-6 pt-10 pb-16 md:pt-16 md:pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* Left Column: Headline, Subtext, CTAs */}
          <div className="lg:col-span-6 flex flex-col items-start z-10">
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="font-mono text-xs uppercase tracking-widest text-navy/60 font-bold mb-4 flex items-center gap-2"
            >
              <span className="w-2 h-2 rounded-full bg-cobalt inline-block animate-pulse" />
              THE FEYNMAN TECHNIQUE, AUTOMATED
            </motion.div>

            {/* Headline with Typewriter Animation */}
            <TypewriterHeadline />

            {/* Subtext */}
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.35 }}
              className="font-sans text-lg md:text-xl text-navy/80 leading-relaxed max-w-xl mb-8"
            >
              Explain what you know. Curio challenges your thinking, uncovers your knowledge gaps, and helps you truly understand.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.5 }}
              className="flex items-center gap-4 flex-wrap"
            >
              <Link href="/topics">
                <KeycapButton variant="navy" size="lg">
                  START LEARNING →
                </KeycapButton>
              </Link>
              <KeycapButton
                variant="ghost"
                size="lg"
                onClick={scrollToHowItWorks}
              >
                EXPLORE HOW CURIO WORKS ↓
              </KeycapButton>
            </motion.div>
          </div>

          {/* Right Column: 3D Knowledge Network Scene */}
          <div className="lg:col-span-6 w-full flex justify-center overflow-visible">
            <Hero3DScene />
          </div>
        </div>
      </section>

      {/* 2. THE PROBLEM VS CURIO */}
      <LearningParadox3D />

      {/* 3. HOW CURIO THINKS (5-Stage Loop) */}
      <HowCurioThinks />

      {/* 4. ADAPTIVE NETWORK TOPOLOGY */}
      <AdaptiveNetworkSection />

      {/* 5. TEACHER MODE INTERACTIVE DEMO */}
      <TeacherModeDemo />

      {/* 6. LEARNING REPORT & GAP MAP */}
      <ReportPreviewSection />

      {/* 7. FINAL CTA */}
      <section className="py-24 border-t border-navy bg-white text-center">
        <div className="max-w-3xl mx-auto px-6">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-cobalt block mb-3">
            START YOUR LABORATORY
          </span>
          <h2 className="font-heading text-4xl sm:text-5xl font-extrabold text-navy tracking-tight mb-6">
            Explain something you know.
          </h2>
          <p className="font-sans text-lg text-navy/75 max-w-xl mx-auto mb-8">
            Pick any algorithm, physical process, or architectural concept. Discover what you truly understand.
          </p>
          <Link href="/topics">
            <KeycapButton variant="navy" size="lg">
              START WITH CURIO →
            </KeycapButton>
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <CurioFooter />
    </div>
  );
}
