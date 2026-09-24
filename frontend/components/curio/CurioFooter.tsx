"use client";

import React from "react";
import Link from "next/link";
import { ArrowUpRight, ChevronUp, Terminal } from "lucide-react";

export function CurioFooter() {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <footer className="relative bg-[#091B2E] text-white border-t-2 border-navy overflow-hidden">
      {/* Decorative technical blueprint grid overlay */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(#3A63FF 1px, transparent 1px), linear-gradient(90deg, #3A63FF 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />

      {/* Subtle top edge accent glow */}
      <div
        aria-hidden="true"
        className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cobalt/60 to-transparent"
      />

      <div className="relative max-w-7xl mx-auto px-6 pt-16 pb-12">
        {/* Main Footer Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-10 lg:gap-12 pb-14 border-b border-white/10">
          {/* Brand & Mission (Col 1-5) */}
          <div className="lg:col-span-5 flex flex-col justify-between">
            <div>
              {/* Brand Logo */}
              <div className="flex items-center gap-3 mb-4">
                <Link
                  href="/"
                  className="font-mono text-2xl font-black tracking-wider text-white hover:text-ice transition-colors inline-flex items-center"
                >
                  CURIO<span className="text-gap-orange">.</span>
                </Link>
                <span className="font-mono text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-[3px] bg-cobalt/20 border border-cobalt/40 text-cobalt text-blue-300">
                  Feynman Lab v2.0
                </span>
              </div>

              {/* Tagline */}
              <p className="font-sans text-sm text-fog/80 leading-relaxed max-w-sm mb-6">
                An adaptive, cognitive learning laboratory inspired by the Feynman
                Technique. Dissect mental models, diagnose hidden blindspots, and
                turn passive recall into structured mastery.
              </p>

              {/* Prominent GitHub Clickable Logo & Badge */}
              <div className="pt-1">
                <a
                  href="https://github.com/joshi-chinmay-016/Curio-AI"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="View Curio AI repository on GitHub"
                  className="group inline-flex items-center gap-3.5 px-4 py-2.5 rounded-md bg-white/[0.06] hover:bg-white/[0.12] border border-white/15 hover:border-cobalt/70 transition-all duration-200 shadow-sm hover:shadow-[0_0_16px_rgba(58,99,255,0.25)]"
                >
                  {/* GitHub Octocat SVG */}
                  <div className="w-6 h-6 flex items-center justify-center text-white group-hover:text-cobalt transition-colors duration-200">
                    <svg
                      role="img"
                      viewBox="0 0 24 24"
                      className="w-5 h-5 fill-current"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <title>GitHub</title>
                      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                    </svg>
                  </div>

                  <div className="flex flex-col text-left">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-fog/70 group-hover:text-fog transition-colors leading-none mb-1">
                      Open Source Repository
                    </span>
                    <span className="font-mono text-xs font-bold text-white group-hover:text-blue-300 transition-colors leading-none flex items-center gap-1.5">
                      Curio-AI
                      <ArrowUpRight className="w-3.5 h-3.5 text-fog/60 group-hover:text-blue-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-200" />
                    </span>
                  </div>
                </a>
              </div>
            </div>

            {/* Live Operational Status */}
            <div className="mt-8 flex items-center gap-2.5 font-mono text-[11px] text-fog/60">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span>Groq Llama 3.3 Engine • Operational</span>
            </div>
          </div>

          {/* Navigation Column 1: Explore (Col 6-7) */}
          <div className="lg:col-span-2">
            <h4 className="font-mono text-xs uppercase font-bold tracking-widest text-white/90 mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cobalt" />
              Explore
            </h4>
            <ul className="space-y-2.5 font-sans text-sm text-fog/80">
              <li>
                <Link
                  href="/topics"
                  className="hover:text-white hover:translate-x-0.5 transition-all inline-block"
                >
                  Topics Catalog
                </Link>
              </li>
              <li>
                <Link
                  href="/history"
                  className="hover:text-white hover:translate-x-0.5 transition-all inline-block"
                >
                  Session History
                </Link>
              </li>
              <li>
                <a
                  href="#how-it-works"
                  className="hover:text-white hover:translate-x-0.5 transition-all inline-block"
                >
                  5-Stage Feynman Loop
                </a>
              </li>
              <li>
                <a
                  href="#teacher-mode"
                  className="hover:text-white hover:translate-x-0.5 transition-all inline-block"
                >
                  Teacher Mode
                </a>
              </li>
            </ul>
          </div>

          {/* Navigation Column 2: System Architecture (Col 8-10) */}
          <div className="lg:col-span-3">
            <h4 className="font-mono text-xs uppercase font-bold tracking-widest text-white/90 mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-gap-orange" />
              Architecture
            </h4>
            <ul className="space-y-2.5 font-sans text-sm text-fog/80">
              <li className="flex items-center justify-between text-xs font-mono text-fog/70">
                <span>Inquiry Engine</span>
                <span className="text-white/40">Socratic</span>
              </li>
              <li className="flex items-center justify-between text-xs font-mono text-fog/70">
                <span>Verification Threshold</span>
                <span className="text-emerald-400 font-bold">≥ 0.70</span>
              </li>
              <li className="flex items-center justify-between text-xs font-mono text-fog/70">
                <span>Knowledge Graph</span>
                <span className="text-white/40">Isometric</span>
              </li>
              <li className="flex items-center justify-between text-xs font-mono text-fog/70">
                <span>Gap Topology</span>
                <span className="text-gap-orange font-bold">3D Voxels</span>
              </li>
            </ul>
          </div>

          {/* Quick Action / Jump to Top (Col 11-12) */}
          <div className="lg:col-span-2 flex flex-col items-start lg:items-end justify-between">
            <div>
              <h4 className="font-mono text-xs uppercase font-bold tracking-widest text-white/90 mb-4">
                Laboratory
              </h4>
              <Link
                href="/topics"
                className="font-mono text-xs font-bold uppercase tracking-wider text-cobalt hover:text-blue-300 transition-colors flex items-center gap-1.5"
              >
                Launch Session →
              </Link>
            </div>

            <button
              onClick={scrollToTop}
              aria-label="Scroll back to top of page"
              className="mt-6 lg:mt-0 group flex items-center gap-2 px-3 py-1.5 rounded bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-white/20 text-fog/70 hover:text-white font-mono text-xs transition-colors"
            >
              <span>TOP</span>
              <ChevronUp className="w-3.5 h-3.5 group-hover:-translate-y-0.5 transition-transform" />
            </button>
          </div>
        </div>

        {/* Bottom Bar: Copyright, Open Source Notice, Tech stack */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-xs text-fog/50">
          <div className="flex items-center gap-2 text-center sm:text-left">
            <span>CURIO AI © {new Date().getFullYear()}</span>
            <span>•</span>
            <span>AN ADAPTIVE LEARNING LABORATORY</span>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <span className="flex items-center gap-1">
              <Terminal className="w-3 h-3 text-cobalt" />
              Next.js 14 • FastAPI • Groq
            </span>
            <span>•</span>
            <a
              href="https://github.com/joshi-chinmay-016/Curio-AI"
              target="_blank"
              rel="noopener noreferrer"
              className="text-fog/70 hover:text-white transition-colors underline underline-offset-4 decoration-white/20 hover:decoration-white"
            >
              GitHub Project
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
