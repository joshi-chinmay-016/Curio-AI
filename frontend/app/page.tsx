"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, BookOpen, Brain, Sparkles } from "lucide-react";
import { CurioNav } from "@/components/curio/CurioNav";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { Hero3DScene } from "@/components/curio/landing/Hero3DScene";
import { HowCurioThinks } from "@/components/curio/landing/HowCurioThinks";
import { AdaptiveNetworkSection } from "@/components/curio/landing/AdaptiveNetworkSection";
import { TeacherModeDemo } from "@/components/curio/landing/TeacherModeDemo";
import { ReportPreviewSection } from "@/components/curio/landing/ReportPreviewSection";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";

export default function LandingPage() {
  const headlineWords = ["Don't", "memorize.", "Explain."];

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

            {/* Headline */}
            <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy tracking-tight leading-[1.08] mb-6">
              {headlineWords.map((word, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: i * 0.08 }}
                  className="inline-block mr-3"
                >
                  {word}
                </motion.span>
              ))}
            </h1>

            {/* Subtext */}
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.35 }}
              className="font-sans text-lg md:text-xl text-navy/80 leading-relaxed max-w-xl mb-8"
            >
              Curio asks you to explain concepts in your own words. Then maps your
              thinking in 3D to uncover exactly where your understanding breaks.
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
          <div className="lg:col-span-6 w-full flex justify-center">
            <Hero3DScene />
          </div>
        </div>
      </section>

      {/* 2. THE PROBLEM VS CURIO */}
      <section id="how-it-works" className="py-20 border-t border-fog bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-xl mx-auto mb-16">
            <span className="font-mono text-xs font-bold uppercase tracking-widest text-navy/50 block mb-2">
              THE LEARNING PARADOX
            </span>
            <h2 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-4">
              Passive Learning Is An Illusion
            </h2>
            <p className="font-sans text-base text-navy/70">
              When you re-read notes or watch lectures, your brain confuses familiarity with true mastery.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Traditional Learning Card */}
            <div className="bg-ice/50 border border-fog rounded-[8px] p-8">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-navy/40 block mb-3">
                TRADITIONAL APPROACH
              </span>
              <h3 className="font-heading text-xl font-bold text-navy mb-4">
                Read → Memorize → Forget
              </h3>
              <ul className="space-y-3 font-sans text-sm text-navy/75">
                <li className="flex items-start gap-2.5">
                  <span className="text-navy/40 font-bold">✗</span>
                  <span>Passive consumption creates false confidence.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-navy/40 font-bold">✗</span>
                  <span>Boundary conditions and edge cases remain hidden until exams or production incidents.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-navy/40 font-bold">✗</span>
                  <span>Generic AI chat gives you answers without challenging your assumptions.</span>
                </li>
              </ul>
            </div>

            {/* Curio Feynman Card */}
            <div className="bg-white border-2 border-navy rounded-[8px] p-8 shadow-[6px_6px_0_0_#0F2B4A]">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-cobalt block mb-3">
                CURIO FEYNMAN SYSTEM
              </span>
              <h3 className="font-heading text-xl font-bold text-navy mb-4">
                Explain → Question → Discover Gaps → Master
              </h3>
              <ul className="space-y-3 font-sans text-sm text-navy/85">
                <li className="flex items-start gap-2.5">
                  <span className="text-cobalt font-bold">✓</span>
                  <span>Teaching forces your brain to structure and articulate mental models.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-gap-orange font-bold">✓</span>
                  <span>Curio actively probes your explanations for exact logical gaps and misconceptions.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-cobalt font-bold">✓</span>
                  <span>Generates a 3D isometric Gap Report mapping exactly what needs deliberate practice.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

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
      <footer className="w-full border-t border-fog bg-ice px-6 py-8 text-center font-mono text-xs text-navy/50">
        CURIO AI © {new Date().getFullYear()} — AN ADAPTIVE LEARNING LABORATORY BASED ON THE FEYNMAN TECHNIQUE
      </footer>
    </div>
  );
}
