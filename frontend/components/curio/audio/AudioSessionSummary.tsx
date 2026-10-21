"use client";

import React from "react";
import Link from "next/link";
import { KeycapButton } from "@/components/curio/KeycapButton";
import {
  Award,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  ArrowRight,
  GraduationCap,
  Sparkles,
  FastForward,
} from "lucide-react";

interface AudioSessionSummaryProps {
  sessionId: string;
  topic: string;
  mode: "STUDENT" | "PROFESSOR";
  understandingScore: number;
  totalQuestions: number;
  totalAnswered: number;
  totalSkipped: number;
  consecutiveUnanswered: number;
  hasEndedByProfessor: boolean;
  strengths?: string[];
  gaps?: string[];
  onRestartSession: () => void;
}

export function AudioSessionSummary({
  sessionId,
  topic,
  mode,
  understandingScore,
  totalQuestions,
  totalAnswered,
  totalSkipped,
  consecutiveUnanswered,
  hasEndedByProfessor,
  strengths = [],
  gaps = [],
  onRestartSession,
}: AudioSessionSummaryProps) {
  const isProf = mode === "PROFESSOR";

  return (
    <div className="w-full max-w-2xl mx-auto p-6 md:p-8 animate-fade-in select-none">
      <div className="bg-white dark:bg-[#0E1A2B] border-2 border-navy dark:border-[#2F4D73] rounded-[12px] p-6 md:p-8 shadow-[6px_6px_0_0_#0F2B4A] dark:shadow-[6px_6px_0_0_#040910]">
        {/* Header Badge */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800/60 rounded-full font-mono text-xs font-bold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider mb-2">
            <Award className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            AUDIO SESSION COMPLETE
          </div>

          <h2 className="font-heading text-2xl md:text-3xl font-extrabold text-navy dark:text-[#F0F4F8] tracking-tight">
            {topic}
          </h2>
          <span className="font-mono text-xs text-navy/50 dark:text-[#829AB1] uppercase font-semibold">
            {isProf ? "Professor Oral Interview" : "Student Teaching Session"}
          </span>
        </div>

        {/* Ended by Professor Alert Banner */}
        {hasEndedByProfessor && (
          <div className="mb-6 p-4 bg-rose-50 dark:bg-rose-950/40 border-2 border-rose-400 dark:border-rose-900/60 rounded-[8px] flex items-start gap-3 text-rose-900 dark:text-rose-200">
            <img
              src="/characters/professor.png"
              alt="Professor Sterling"
              className="w-12 h-14 object-cover rounded-[6px] border border-rose-300 dark:border-rose-800/60 shrink-0"
            />
            <div>
              <span className="font-heading text-sm font-bold block text-rose-950 dark:text-rose-100">
                Interview Concluded by Professor Sterling
              </span>
              <p className="font-sans text-xs text-rose-800 dark:text-rose-300 leading-relaxed mt-0.5">
                The interview was concluded after reaching the threshold of 3 consecutive unanswered questions or skips. Review the identified gaps below before testing again.
              </p>
            </div>
          </div>
        )}

        {/* Score & Key Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-ice/60 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[8px] p-3 text-center">
            <span className="font-mono text-[10px] uppercase font-bold text-navy/50 dark:text-[#829AB1] block">
              Confidence
            </span>
            <span className="font-mono text-2xl font-extrabold text-navy dark:text-[#F0F4F8]">
              {understandingScore}%
            </span>
          </div>

          <div className="bg-ice/60 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[8px] p-3 text-center">
            <span className="font-mono text-[10px] uppercase font-bold text-navy/50 dark:text-[#829AB1] block">
              Questions
            </span>
            <span className="font-mono text-2xl font-extrabold text-navy dark:text-[#F0F4F8]">
              {totalQuestions}
            </span>
          </div>

          <div className="bg-ice/60 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[8px] p-3 text-center">
            <span className="font-mono text-[10px] uppercase font-bold text-emerald-700 dark:text-emerald-400 block">
              Answered
            </span>
            <span className="font-mono text-2xl font-extrabold text-emerald-700 dark:text-emerald-400">
              {totalAnswered}
            </span>
          </div>

          <div className="bg-ice/60 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[8px] p-3 text-center">
            <span className="font-mono text-[10px] uppercase font-bold text-gap-orange block">
              Skipped
            </span>
            <span className="font-mono text-2xl font-extrabold text-gap-orange">
              {totalSkipped}
            </span>
          </div>
        </div>

        {/* Strengths & Gaps */}
        <div className="space-y-4 mb-8">
          {strengths.length > 0 && (
            <div className="bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/40 rounded-[8px] p-4">
              <span className="font-mono text-xs font-bold text-emerald-900 dark:text-emerald-300 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                VERIFIED STRENGTHS:
              </span>
              <ul className="list-disc list-inside space-y-1 font-sans text-xs text-emerald-950 dark:text-emerald-200">
                {strengths.map((s, idx) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {gaps.length > 0 && (
            <div className="bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/40 rounded-[8px] p-4">
              <span className="font-mono text-xs font-bold text-amber-900 dark:text-amber-300 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <AlertTriangle className="w-4 h-4 text-gap-orange" />
                IDENTIFIED KNOWLEDGE GAPS:
              </span>
              <ul className="list-disc list-inside space-y-1 font-sans text-xs text-amber-950 dark:text-amber-200">
                {gaps.map((g, idx) => (
                  <li key={idx}>{g}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-fog dark:border-[#1E3652]">
          <Link href="/dashboard">
            <KeycapButton variant="ghost" size="md">
              ← RETURN TO DASHBOARD
            </KeycapButton>
          </Link>

          <div className="flex items-center gap-2">
            <KeycapButton onClick={onRestartSession} variant="default" size="md">
              <span className="inline-flex items-center gap-1.5">
                <RotateCcw className="w-3.5 h-3.5" />
                NEW AUDIO SESSION
              </span>
            </KeycapButton>

            <Link href={`/session/${sessionId}/report`}>
              <KeycapButton variant="navy" size="md">
                <span className="inline-flex items-center gap-1.5">
                  VIEW REPORT <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </KeycapButton>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
