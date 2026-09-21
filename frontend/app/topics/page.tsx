"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Search } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { curioToast } from "@/components/curio/CurioToast";
import { startSession } from "@/services/sessionService";
import { getSessionHistory } from "@/services/historyService";
import { SessionSummary } from "@/types/history";
import { useSessionStore } from "@/stores/sessionStore";

export default function TopicSelectionPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([]);

  const suggestedTopics = [
    "Binary Search",
    "QuickSort & Partitioning",
    "Binary Search Trees",
    "Dijkstra's Algorithm",
    "Dynamic Programming (0/1 Knapsack)",
    "Hash Tables & Collision Resolution",
    "Breadth-First Search (BFS)",
    "Recursion & Call Stack",
  ];

  useEffect(() => {
    getSessionHistory().then((data) => {
      setRecentSessions(data.slice(0, 3));
    });
  }, []);

  const { setTopic } = useSessionStore();

  const handleStart = async (topicToStart?: string) => {
    const topic = (topicToStart || query).trim();
    if (!topic) return;

    setLoading(true);
    try {
      const res = await startSession(topic);
      setTopic(topic, res.sessionId);
      curioToast.success("SESSION CREATED", `Let's explore ${topic}.`);
      router.push(`/session/${res.sessionId}?topic=${encodeURIComponent(topic)}`);
    } catch {
      curioToast.error("COULDN'T START SESSION. TRY AGAIN.");
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleStart();
    }
  };

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
              CURIO / SELECT A TOPIC
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10 md:py-16">
        <div className="text-center max-w-xl mx-auto mb-10">
          <h1 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-3">
            What do you want to teach?
          </h1>
          <p className="font-sans text-base text-navy/70">
            Enter any concept, algorithm, or idea. Curio will adapt to your explanations.
          </p>
        </div>

        {/* Search Input Box */}
        <div className="bg-white border-2 border-navy rounded-[6px] shadow-[0_4px_0_0_#0F2B4A] p-3 flex items-center gap-3 mb-8 transition-all duration-150 focus-within:border-cobalt">
          <Search className="w-5 h-5 text-navy/40 ml-2 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter a topic to teach Curio..."
            disabled={loading}
            className="w-full bg-transparent font-sans text-base text-navy placeholder:text-navy/40 focus:outline-none py-1"
          />
          <KeycapButton
            variant="navy"
            size="md"
            loading={loading}
            loadingText="PREPARING..."
            disabled={!query.trim() || loading}
            onClick={() => handleStart()}
            className="shrink-0"
          >
            TEACH THIS →
          </KeycapButton>
        </div>

        {/* Suggested Topics Chips */}
        <div className="mb-14">
          <div className="font-mono text-xs uppercase tracking-wider text-navy/50 font-bold mb-3">
            SUGGESTED TOPICS
          </div>
          <div className="flex flex-wrap gap-2.5">
            {suggestedTopics.map((topic) => (
              <button
                key={topic}
                onClick={() => {
                  setQuery(topic);
                }}
                className="font-mono text-xs uppercase font-semibold px-3 py-2 rounded-[4px] bg-white border border-navy text-navy hover:bg-navy hover:text-white transition-colors select-none shadow-[0_2px_0_0_#0F2B4A]"
              >
                {topic}
              </button>
            ))}
          </div>
        </div>

        {/* Recent Sessions */}
        {recentSessions.length > 0 && (
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-navy/50 font-bold mb-4 flex items-center justify-between">
              <span>RECENT SESSIONS</span>
              <Link
                href="/history"
                className="font-mono text-xs text-cobalt hover:underline uppercase"
              >
                VIEW ALL →
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {recentSessions.map((session) => (
                <div
                  key={session.sessionId}
                  className="bg-white border border-fog rounded-[6px] p-4 shadow-sm hover:border-cobalt transition-colors flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-1 mb-1">
                      <h4 className="font-heading text-sm font-bold text-navy truncate">
                        {session.topicName}
                      </h4>
                      <span className="font-mono text-xs font-bold text-cobalt shrink-0">
                        {session.understandingScore}/100
                      </span>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[11px] text-navy/60 mb-3">
                      <span>{session.masteryLevel}</span>
                      <span>·</span>
                      <span>
                        {new Date(session.createdAt).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-fog/60 flex items-center justify-between gap-2">
                    <Link
                      href={`/session/${session.sessionId}/report`}
                      className="text-xs font-mono text-navy/70 hover:text-navy uppercase font-semibold"
                    >
                      REPORT
                    </Link>
                    <Link href={`/session/${session.sessionId}`}>
                      <KeycapButton variant="cobalt" size="sm">
                        RESTORE
                      </KeycapButton>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
