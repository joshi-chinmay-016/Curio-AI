"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Mic, Sparkles } from "lucide-react";
import { CurioNav } from "@/components/curio/CurioNav";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { StudentCharacter } from "@/components/character/characters/StudentCharacter";
import { TeacherCharacter } from "@/components/character/characters/TeacherCharacter";
import { ProfessorCharacter } from "@/components/character/characters/ProfessorCharacter";
import { CharacterStage } from "@/components/character/CharacterStage";
import { CharacterId, PerformanceState } from "@/types/performanceEngine";

export default function CharacterGalleryPage() {
  const [character, setCharacter] = useState<CharacterId>("STUDENT");
  const [performance, setPerformance] = useState<PerformanceState>("IDLE");
  const [clipboardMark, setClipboardMark] = useState<"none" | "check" | "cross">("check");
  const [viewMode, setViewMode] = useState<"interactive" | "grid">("grid");

  return (
    <div className="min-h-screen bg-[#070F1B] text-white flex flex-col items-center">
      {/* Global Navigation Header */}
      <CurioNav activeRoute="characters" />

      {/* Main Container */}
      <div className="w-full max-w-6xl p-6 flex flex-col items-center">
        {/* Top Header */}
        <div className="w-full text-center mb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cobalt/15 border border-cobalt/30 text-cobalt text-xs font-mono font-semibold uppercase tracking-wider mb-2">
          Curio AI Engine
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-2">
          Curio AI — Animated Character Showcase
        </h1>
        <p className="text-sm md:text-base text-slate-400 max-w-2xl mx-auto">
          Recreated from reference assets as layered vector SVGs with independent Framer Motion animations across all performance states.
        </p>

        {/* View Switcher */}
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setViewMode("grid")}
            className={`px-4 py-1.5 rounded-xl text-xs font-mono font-bold transition-all ${
              viewMode === "grid"
                ? "bg-cobalt text-white shadow-lg shadow-cobalt/30"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
          >
            Grid: All 9 Required Delivery States
          </button>
          <button
            onClick={() => setViewMode("interactive")}
            className={`px-4 py-1.5 rounded-xl text-xs font-mono font-bold transition-all ${
              viewMode === "interactive"
                ? "bg-cobalt text-white shadow-lg shadow-cobalt/30"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
          >
            Interactive Stage Controls
          </button>
        </div>
      </div>

      {/* ========================================================
          VIEW 1: ALL 9 REQUIRED DELIVERY STATES GRID
          ======================================================== */}
      {viewMode === "grid" && (
        <div className="max-w-6xl w-full flex flex-col gap-10">
          {/* 1. STUDENT ROW */}
          <div className="bg-[#0B1728] border border-cobalt/30 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4 border-b border-cobalt/20 pb-3">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-cobalt inline-block" />
                  Student — Leo
                </h2>
                <p className="text-xs text-slate-400">
                  Approachability, headphones, blue shirt, dark backpack, note-taking scribbles
                </p>
              </div>
              <span className="px-3 py-1 rounded-full bg-cobalt/20 text-cobalt text-xs font-mono font-semibold">
                Reference: student.png
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Student State 1: IDLE */}
              <div
                id="card-student-idle"
                className="bg-[#06101E] border border-slate-700/60 rounded-2xl p-4 flex flex-col items-center"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-slate-300">1. IDLE</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Gentle breathing, blinking
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <StudentCharacter performance="IDLE" />
                </div>
              </div>

              {/* Student State 2: LISTENING */}
              <div
                id="card-student-listening"
                className="bg-[#06101E] border border-cobalt/50 rounded-2xl p-4 flex flex-col items-center relative overflow-hidden"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-cobalt">2. LISTENING</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cobalt/20 text-cobalt">
                    Attentive tilt + soundwave pulse
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <StudentCharacter performance="LISTENING_ACTIVE" />
                </div>
              </div>

              {/* Student State 3: TAKING_NOTES */}
              <div
                id="card-student-notes"
                className="bg-[#06101E] border border-emerald-500/50 rounded-2xl p-4 flex flex-col items-center relative overflow-hidden"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-emerald-400">3. TAKING_NOTES</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300">
                    Signature State: Notebook + Pen
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <StudentCharacter performance="TAKING_NOTES" />
                </div>
              </div>
            </div>
          </div>

          {/* 2. TEACHER ROW */}
          <div className="bg-[#0B1728] border border-orange-500/30 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4 border-b border-orange-500/20 pb-3">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-orange-500 inline-block" />
                  Teacher — Ms. Clara
                </h2>
                <p className="text-xs text-slate-400">
                  Voluminous curly hair, round glasses, cream cardigan, pleated skirt, book prop
                </p>
              </div>
              <span className="px-3 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs font-mono font-semibold">
                Reference: teacher.png
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Teacher State 1: IDLE */}
              <div
                id="card-teacher-idle"
                className="bg-[#06101E] border border-slate-700/60 rounded-2xl p-4 flex flex-col items-center"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-slate-300">1. IDLE</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Resting book, warm posture
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <TeacherCharacter performance="IDLE" />
                </div>
              </div>

              {/* Teacher State 2: LISTENING */}
              <div
                id="card-teacher-listening"
                className="bg-[#06101E] border border-orange-500/50 rounded-2xl p-4 flex flex-col items-center"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-orange-400">2. LISTENING</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/20 text-orange-400">
                    Encouraging listening tilt
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <TeacherCharacter performance="LISTENING_ACTIVE" />
                </div>
              </div>

              {/* Teacher State 3: EXPLAINING */}
              <div
                id="card-teacher-explaining"
                className="bg-[#06101E] border border-emerald-500/50 rounded-2xl p-4 flex flex-col items-center"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-emerald-400">3. EXPLAINING</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300">
                    Signature State: Book Lifts & Hand Gestures
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <TeacherCharacter performance="EXPLAINING" />
                </div>
              </div>
            </div>
          </div>

          {/* 3. PROFESSOR ROW */}
          <div className="bg-[#0B1728] border border-slate-600/40 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4 border-b border-slate-700/40 pb-3">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-slate-300 inline-block" />
                  Professor — Prof. Sterling
                </h2>
                <p className="text-xs text-slate-400">
                  White hair, prominent white moustache, spectacles, navy suit, authoritative folded arms
                </p>
              </div>
              <span className="px-3 py-1 rounded-full bg-slate-700/40 text-slate-300 text-xs font-mono font-semibold">
                Reference: professor.png
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Professor State 1: IDLE */}
              <div
                id="card-professor-idle"
                className="bg-[#06101E] border border-slate-700/60 rounded-2xl p-4 flex flex-col items-center"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-slate-300">1. IDLE</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Arms folded across chest
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <ProfessorCharacter performance="IDLE" />
                </div>
              </div>

              {/* Professor State 2: LISTENING */}
              <div
                id="card-professor-listening"
                className="bg-[#06101E] border border-amber-500/50 rounded-2xl p-4 flex flex-col items-center"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-amber-400">2. LISTENING</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">
                    Stern attentive gaze
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <ProfessorCharacter performance="LISTENING_ACTIVE" />
                </div>
              </div>

              {/* Professor State 3: EVALUATING */}
              <div
                id="card-professor-evaluating"
                className="bg-[#06101E] border border-emerald-500/50 rounded-2xl p-4 flex flex-col items-center"
              >
                <div className="w-full flex justify-between items-center mb-2">
                  <span className="text-xs font-mono font-bold text-emerald-400">3. EVALUATING</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300">
                    Signature State: Clipboard Assessment
                  </span>
                </div>
                <div className="w-[200px] h-[270px] relative">
                  <ProfessorCharacter performance="EVALUATING" clipboardMark="check" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          VIEW 2: INTERACTIVE STAGE CONTROLS
          ======================================================== */}
      {viewMode === "interactive" && (
        <div className="flex flex-col md:flex-row items-center justify-center gap-8 w-full max-w-4xl">
          <div id="character-showcase-stage" className="flex flex-col items-center">
            <CharacterStage
              character={character}
              performanceState={performance}
              clipboardMark={clipboardMark}
            />
          </div>

          <div className="w-full max-w-xs bg-[#0D1D33] border border-slate-700/60 rounded-2xl p-5 flex flex-col gap-3">
            <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
              Select Character
            </div>
            <div className="flex gap-2">
              {(["STUDENT", "TEACHER", "PROFESSOR"] as const).map((c) => (
                <button
                  key={c}
                  onClick={() => setCharacter(c)}
                  className={`flex-1 py-1.5 text-xs font-mono font-bold rounded-lg transition-all ${
                    character === c
                      ? "bg-cobalt text-white shadow-md"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>

            <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider mt-2">
              Performance State
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                "IDLE",
                "LISTENING_ACTIVE",
                "THINKING",
                "SPEAKING",
                "ASKING",
                "TAKING_NOTES",
                "EXPLAINING",
                "EVALUATING",
                "REACTING_POSITIVE",
                "REACTING_CONFUSED",
                "REACTING_STRICT",
                "REACTING_GRUMPY",
              ].map((st) => (
                <button
                  key={st}
                  onClick={() => setPerformance(st as PerformanceState)}
                  className={`px-2 py-1 text-[11px] font-mono rounded-lg transition-all ${
                    performance === st
                      ? "bg-emerald-500 text-black font-bold"
                      : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            {character === "PROFESSOR" && (
              <div className="flex justify-between items-center text-sm border-t border-slate-700/50 pt-2 mt-2">
                <span className="text-xs text-slate-400 font-mono">Clipboard Mark:</span>
                <div className="flex gap-1.5">
                  {(["check", "cross", "none"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setClipboardMark(m)}
                      className={`px-2 py-0.5 text-xs font-mono rounded ${
                        clipboardMark === m ? "bg-slate-600 text-white" : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

        {/* Bottom Audio Learning CTA Banner */}
        <div className="w-full mt-12 mb-8 p-6 rounded-xl bg-gradient-to-r from-slate-900 via-navy to-slate-900 border border-slate-700/80 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
          <div className="text-left">
            <span className="font-mono text-xs font-bold text-gap-orange uppercase tracking-wider block mb-1">
              Ready to talk?
            </span>
            <h3 className="font-heading text-lg font-bold text-white">
              Speak with these animated AI characters using live voice
            </h3>
            <p className="font-sans text-xs text-slate-300">
              Interactive voice conversations with speech-to-speech and synchronized expressions.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link href="/dashboard">
              <KeycapButton variant="ghost" size="sm" className="text-white border-white/40 hover:bg-white/10 hover:text-white">
                DASHBOARD
              </KeycapButton>
            </Link>
            <Link href="/audio-learning">
              <KeycapButton variant="gap" size="sm">
                <span className="inline-flex items-center gap-1.5 font-bold">
                  <Mic className="w-4 h-4 text-gap-orange" />
                  START AUDIO SESSION →
                </span>
              </KeycapButton>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
