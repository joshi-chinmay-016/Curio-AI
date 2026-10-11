"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Brain,
  Sparkles,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  Play,
  RotateCcw,
  LogOut,
  Layers,
  Award,
  AlertTriangle,
  History,
} from "lucide-react";
import { ProtectedRoute } from "@/components/curio/auth/ProtectedRoute";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { useAuthStore } from "@/stores/authStore";
import { getSessionHistory } from "@/services/historyService";
import { getUserProgress } from "@/services/progressService";
import { SessionSummary } from "@/types/history";
import { LearningProgressData } from "@/types/progress";

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

function DashboardContent() {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [progressData, setProgressData] = useState<LearningProgressData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        const [historyRes, progressRes] = await Promise.allSettled([
          getSessionHistory(1, 10),
          getUserProgress(),
        ]);

        if (mounted) {
          if (historyRes.status === "fulfilled") {
            setSessions(historyRes.value);
          }
          if (progressRes.status === "fulfilled") {
            setProgressData(progressRes.value);
          }
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  const displayName = user?.email ? user.email.split("@")[0] : "Learner";
  const activeSession = sessions.find((s) => s.status === "IN_PROGRESS");
  const completedSessionsCount = sessions.filter((s) => s.status === "COMPLETED").length;
  const totalConceptsTracked = progressData?.summary?.total_concepts_tracked || progressData?.concepts?.length || 0;
  const totalMisconceptions = progressData?.summary?.total_misconceptions || 0;

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Authenticated Application Shell Header */}
      <header className="w-full bg-white border-b border-fog px-6 py-4 sticky top-0 z-30 shadow-xs">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link
              href="/"
              className="font-mono text-xl font-bold tracking-wider text-navy hover:text-cobalt transition-colors"
            >
              CURIO<span className="text-gap-orange">.</span>
            </Link>

            <nav className="hidden md:flex items-center gap-5 text-xs font-mono font-semibold uppercase">
              <Link
                href="/dashboard"
                className="text-cobalt border-b-2 border-cobalt pb-0.5 transition-colors"
              >
                DASHBOARD
              </Link>
              <Link
                href="/history"
                className="text-navy/70 hover:text-navy transition-colors pb-0.5"
              >
                HISTORY
              </Link>
              <Link
                href="/topics"
                className="text-navy/70 hover:text-navy transition-colors pb-0.5"
              >
                TOPICS
              </Link>
            </nav>
          </div>

          {/* User Profile & Actions */}
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2.5 px-3 py-1.5 bg-ice/60 border border-fog/80 rounded-[6px]">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-mono text-xs text-navy/80 font-medium truncate max-w-[160px]">
                {user?.email}
              </span>
            </div>

            <button
              onClick={() => {
                logout();
                router.replace("/");
              }}
              title="Sign Out"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono uppercase font-bold text-navy/70 hover:text-red-700 hover:bg-red-50 border border-fog rounded-[6px] transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">LOGOUT</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Dashboard Stage */}
      <main className="max-w-6xl w-full mx-auto px-6 py-8 md:py-12 flex-1">
        {/* Welcome Section */}
        <section className="mb-10">
          <div className="bg-white border-2 border-navy rounded-[10px] p-6 md:p-8 shadow-[6px_6px_0_0_#0F2B4A] relative overflow-hidden">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-ice rounded-[4px] border border-fog text-[10px] font-mono uppercase tracking-widest text-navy/70 font-bold mb-3">
                <span className="w-2 h-2 rounded-full bg-cobalt" />
                LEARNER WORKSPACE
              </div>

              <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-navy tracking-tight mb-2">
                Welcome back, {displayName}.
              </h1>
              <p className="font-sans text-sm md:text-base text-navy/70 leading-relaxed mb-6">
                Ready to reverse roles? Explain what you know to Curio, stress-test your understanding against edge cases, and discover your mental models.
              </p>

              <div className="flex flex-wrap items-center gap-3">
                <Link href="/topics">
                  <KeycapButton variant="navy" size="md">
                    <span className="inline-flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-gap-orange" />
                      TEACH CURIO SOMETHING NEW
                    </span>
                  </KeycapButton>
                </Link>

                <Link href="/history">
                  <KeycapButton variant="default" size="md">
                    <span className="inline-flex items-center gap-2">
                      <History className="w-4 h-4" />
                      VIEW FULL HISTORY
                    </span>
                  </KeycapButton>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Resumable Session Alert (if user has active session) */}
        {activeSession && (
          <section className="mb-10">
            <div className="bg-amber-50/80 border-2 border-amber-500/80 rounded-[8px] p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
              <div className="flex items-start gap-3.5">
                <div className="p-2 bg-amber-100 rounded-md text-amber-800 shrink-0 mt-0.5">
                  <Play className="w-4 h-4" />
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-amber-800 font-bold block mb-1">
                    IN-PROGRESS SESSION DETECTED
                  </span>
                  <h3 className="font-heading text-base font-bold text-navy">
                    {activeSession.topicName}
                  </h3>
                  <p className="font-sans text-xs text-navy/70">
                    Confidence: {activeSession.understandingScore}% · {activeSession.turnCount} turns completed
                  </p>
                </div>
              </div>

              <Link href={`/session/${activeSession.sessionId}`} className="shrink-0">
                <KeycapButton variant="navy" size="sm">
                  <span className="inline-flex items-center gap-1.5">
                    CONTINUE LEARNING <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </KeycapButton>
              </Link>
            </div>
          </section>
        )}

        {/* Metrics Grid */}
        <section className="mb-10">
          <h2 className="font-mono text-xs uppercase tracking-wider text-navy/50 font-bold mb-4">
            LEARNING OVERVIEW & PROGRESS
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Total Sessions */}
            <div className="bg-white border border-fog rounded-[8px] p-5 shadow-xs">
              <div className="flex items-center justify-between text-navy/50 mb-2">
                <span className="font-mono text-xs uppercase font-semibold">Total Sessions</span>
                <BookOpen className="w-4 h-4" />
              </div>
              <div className="font-mono text-2xl md:text-3xl font-extrabold text-navy">
                {sessions.length}
              </div>
              <span className="font-sans text-[11px] text-navy/50 mt-1 block">
                {completedSessionsCount} completed
              </span>
            </div>

            {/* Concepts Tracked */}
            <div className="bg-white border border-fog rounded-[8px] p-5 shadow-xs">
              <div className="flex items-center justify-between text-cobalt mb-2">
                <span className="font-mono text-xs uppercase font-semibold">Concepts</span>
                <Brain className="w-4 h-4" />
              </div>
              <div className="font-mono text-2xl md:text-3xl font-extrabold text-navy">
                {totalConceptsTracked}
              </div>
              <span className="font-sans text-[11px] text-navy/50 mt-1 block">
                Across active topics
              </span>
            </div>

            {/* Misconceptions */}
            <div className="bg-white border border-fog rounded-[8px] p-5 shadow-xs">
              <div className="flex items-center justify-between text-gap-orange mb-2">
                <span className="font-mono text-xs uppercase font-semibold">Misconceptions</span>
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="font-mono text-2xl md:text-3xl font-extrabold text-navy">
                {totalMisconceptions}
              </div>
              <span className="font-sans text-[11px] text-navy/50 mt-1 block">
                Detected & targeted
              </span>
            </div>

            {/* Mastery Gate */}
            <div className="bg-white border border-fog rounded-[8px] p-5 shadow-xs">
              <div className="flex items-center justify-between text-emerald-600 mb-2">
                <span className="font-mono text-xs uppercase font-semibold">Mastery Gate</span>
                <Award className="w-4 h-4" />
              </div>
              <div className="font-mono text-2xl md:text-3xl font-extrabold text-navy">
                {progressData?.concepts?.filter((c) => c.mastery_score >= 0.8).length || 0}
              </div>
              <span className="font-sans text-[11px] text-navy/50 mt-1 block">
                Verified high-mastery
              </span>
            </div>
          </div>
        </section>

        {/* Two-Column Stage: Recent Sessions + Tracked Concepts */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left: Recent Activity */}
          <div className="lg:col-span-7">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-mono text-xs uppercase tracking-wider text-navy/50 font-bold">
                RECENT LEARNING SESSIONS
              </h2>
              <Link href="/history" className="font-mono text-xs text-cobalt hover:underline font-bold">
                VIEW ALL →
              </Link>
            </div>

            {loading ? (
              <div className="bg-white border border-fog rounded-[8px] p-8 text-center font-mono text-xs text-navy/50 animate-pulse">
                LOADING SESSIONS...
              </div>
            ) : sessions.length === 0 ? (
              <div className="bg-white border border-fog rounded-[8px] p-8 text-center">
                <BookOpen className="w-8 h-8 text-navy/30 mx-auto mb-3" />
                <h3 className="font-heading text-base font-bold text-navy mb-1">
                  No sessions recorded yet
                </h3>
                <p className="font-sans text-xs text-navy/60 max-w-sm mx-auto mb-5 leading-relaxed">
                  Start teaching Curio to build your personalized mental models and track conceptual progress.
                </p>
                <Link href="/topics">
                  <KeycapButton variant="navy" size="sm">
                    START FIRST SESSION →
                  </KeycapButton>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {sessions.slice(0, 5).map((session) => (
                  <div
                    key={session.sessionId}
                    className="bg-white border border-fog hover:border-navy/60 rounded-[8px] p-4.5 flex items-center justify-between gap-4 transition-all hover:shadow-xs group"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`inline-block w-2 h-2 rounded-full ${
                            session.status === "COMPLETED" ? "bg-emerald-500" : "bg-amber-500"
                          }`}
                        />
                        <span className="font-mono text-[10px] uppercase font-bold tracking-wider text-navy/50">
                          {session.status}
                        </span>
                        <span className="text-fog">·</span>
                        <span className="font-sans text-xs text-navy/50">
                          {session.createdAt ? new Date(session.createdAt).toLocaleDateString() : ""}
                        </span>
                      </div>

                      <h3 className="font-heading text-sm font-bold text-navy truncate group-hover:text-cobalt transition-colors">
                        {session.topicName}
                      </h3>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div className="text-right hidden sm:block">
                        <span className="font-mono text-xs font-bold text-navy block">
                          {session.understandingScore}%
                        </span>
                        <span className="font-sans text-[10px] text-navy/50 block">
                          {session.masteryLevel}
                        </span>
                      </div>

                      <Link href={`/session/${session.sessionId}`}>
                        <KeycapButton variant="ghost" size="sm">
                          OPEN →
                        </KeycapButton>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Tracked Concepts Mastery */}
          <div className="lg:col-span-5">
            <h2 className="font-mono text-xs uppercase tracking-wider text-navy/50 font-bold mb-4">
              CONCEPT MASTERY & REVIEWS
            </h2>

            {loading ? (
              <div className="bg-white border border-fog rounded-[8px] p-8 text-center font-mono text-xs text-navy/50 animate-pulse">
                LOADING CONCEPTS...
              </div>
            ) : !progressData || progressData.concepts.length === 0 ? (
              <div className="bg-white border border-fog rounded-[8px] p-8 text-center">
                <Brain className="w-8 h-8 text-navy/30 mx-auto mb-3" />
                <h3 className="font-heading text-base font-bold text-navy mb-1">
                  No concepts mapped yet
                </h3>
                <p className="font-sans text-xs text-navy/60 leading-relaxed mb-4">
                  As you answer Curio&apos;s probing questions, concepts and mastery levels will populate here automatically.
                </p>
                <Link href="/topics">
                  <KeycapButton variant="default" size="sm">
                    EXPLORE TOPICS →
                  </KeycapButton>
                </Link>
              </div>
            ) : (
              <div className="bg-white border border-fog rounded-[8px] p-5 space-y-4">
                {progressData.concepts.slice(0, 6).map((concept, idx) => {
                  const pct = Math.round(concept.mastery_score * 100);
                  return (
                    <div key={idx} className="border-b border-fog/50 pb-3 last:border-b-0 last:pb-0">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-heading text-xs font-bold text-navy truncate max-w-[200px]">
                          {concept.concept}
                        </span>
                        <span className="font-mono text-xs font-bold text-navy">
                          {pct}%
                        </span>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full h-1.5 bg-ice rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-cobalt" : "bg-gap-orange"
                          }`}
                          style={{ width: `${Math.max(5, pct)}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between mt-1 text-[10px] font-mono text-navy/50">
                        <span>Attempts: {concept.total_attempts}</span>
                        {concept.misconception_count > 0 && (
                          <span className="text-gap-orange font-semibold">
                            {concept.misconception_count} misconception{concept.misconception_count > 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
