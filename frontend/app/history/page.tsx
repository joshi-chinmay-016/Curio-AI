"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, Layers, Sparkles } from "lucide-react";
import { ProtectedRoute } from "@/components/curio/auth/ProtectedRoute";
import { CurioNav } from "@/components/curio/CurioNav";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { SessionFilter, HistoryFilterType } from "@/components/curio/history/SessionFilter";
import { SessionCard } from "@/components/curio/history/SessionCard";
import { PracticeQueueCard } from "@/components/curio/history/PracticeQueueCard";
import { getSessionHistory, getPracticeQueue } from "@/services/historyService";
import { SessionSummary, PracticeQueueItem } from "@/types/history";

export default function SessionHistoryPage() {
  return (
    <ProtectedRoute>
      <SessionHistoryContent />
    </ProtectedRoute>
  );
}

function SessionHistoryContent() {
  const [filter, setFilter] = useState<HistoryFilterType>("ALL");
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [practiceQueue, setPracticeQueue] = useState<PracticeQueueItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([getSessionHistory(), getPracticeQueue()]).then(
      ([hist, queue]) => {
        if (mounted) {
          setSessions(hist);
          setPracticeQueue(queue);
          setLoading(false);
        }
      }
    );
    return () => {
      mounted = false;
    };
  }, []);

  const filteredSessions = sessions.filter((s) => {
    if (filter === "ALL") return true;
    if (filter === "IN_PROGRESS") return s.status === "IN_PROGRESS";
    if (filter === "COMPLETED") return s.status === "COMPLETED";
    return false;
  });

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Global Navigation */}
      <CurioNav activeRoute="history" />

      {/* Sub-bar with Breadcrumb & Quick Actions */}
      <div className="w-full bg-white/70 border-b border-fog/80 px-6 py-2.5">
        <div className="max-w-4xl mx-auto flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-navy/60">
            <Link href="/dashboard" className="hover:text-navy transition-colors">
              DASHBOARD
            </Link>
            <span className="text-fog">/</span>
            <span className="font-bold text-navy">LEARNING HISTORY</span>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/audio-learning"
              className="hidden sm:inline-flex items-center gap-1.5 text-gap-orange hover:text-gap-orange/80 font-bold transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>AUDIO PRACTICE</span>
            </Link>
            <Link href="/topics">
              <KeycapButton variant="navy" size="sm">
                NEW SESSION +
              </KeycapButton>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10">
        <div className="mb-6">
          <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-navy tracking-tight mb-2">
            Your Learning History
          </h1>
          <p className="font-sans text-sm text-navy/70">
            Review your past explanations, track concept mastery, and practice identified gaps.
          </p>
        </div>

        {/* Filter Strip */}
        <SessionFilter
          activeFilter={filter}
          onFilterChange={setFilter}
          practiceQueueCount={practiceQueue.length}
        />

        {/* Content List */}
        {loading ? (
          <div className="py-20 text-center font-mono text-xs uppercase tracking-widest text-navy/50 flex items-center justify-center gap-2">
            <span className="w-4 h-4 border-2 border-cobalt border-t-transparent rounded-full animate-spin" />
            LOADING SESSIONS...
          </div>
        ) : filter === "PRACTICE_QUEUE" ? (
          /* Practice Queue View */
          practiceQueue.length > 0 ? (
            <div className="space-y-4">
              {practiceQueue.map((item) => (
                <PracticeQueueCard key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <div className="bg-white border border-fog rounded-[8px] p-12 text-center shadow-xs">
              <h3 className="font-heading text-lg font-bold text-navy mb-2">
                Practice Queue Empty
              </h3>
              <p className="font-sans text-sm text-navy/60 max-w-md mx-auto mb-6">
                You have no gaps saved for later. When exploring a Gap Report, click &quot;Save for Later&quot; to queue specific concepts for targeted practice.
              </p>
              <Link href="/topics">
                <KeycapButton variant="navy" size="md">
                  START LEARNING A TOPIC →
                </KeycapButton>
              </Link>
            </div>
          )
        ) : filteredSessions.length > 0 ? (
          /* Sessions List View */
          <div className="space-y-4">
            {filteredSessions.map((session) => (
              <SessionCard key={session.sessionId} session={session} />
            ))}
          </div>
        ) : (
          /* Empty State */
          <div className="bg-white border border-fog rounded-[8px] p-12 text-center shadow-xs">
            <h3 className="font-heading text-lg font-bold text-navy mb-2">
              No sessions found
            </h3>
            <p className="font-sans text-sm text-navy/60 max-w-md mx-auto mb-6">
              You haven&apos;t recorded any sessions under this filter yet. Teach Curio any concept to identify your understanding gaps.
            </p>
            <Link href="/topics">
              <KeycapButton variant="navy" size="md">
                START FIRST SESSION →
              </KeycapButton>
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
