"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Search, FileText, Layers, Sparkles } from "lucide-react";
import { CurioNav } from "@/components/curio/CurioNav";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { curioToast } from "@/components/curio/CurioToast";
import { startSession } from "@/services/sessionService";
import { getSessionHistory } from "@/services/historyService";
import { listDocuments } from "@/services/documentService";
import { SessionSummary } from "@/types/history";
import { DocumentItem } from "@/types/document";
import { useSessionStore } from "@/stores/sessionStore";

export default function TopicSelectionPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([]);
  const [readyDocs, setReadyDocs] = useState<DocumentItem[]>([]);

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
    listDocuments(1, 4)
      .then((res) => {
        const ready = (res.documents || []).filter((d) => d.status === "PROCESSED");
        setReadyDocs(ready);
      })
      .catch(() => {});
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

  const handleStartFromDocument = async (doc: DocumentItem) => {
    const cleanTopic = doc.filename.replace(/\.[^/.]+$/, "").trim() || "Document Learning";
    setLoading(true);
    try {
      const res = await startSession(cleanTopic, {
        sourceType: "DOCUMENT",
        documentId: doc.document_id,
      });
      setTopic(cleanTopic, res.sessionId, "DOCUMENT", doc.document_id);
      curioToast.success("GROUNDED SESSION CREATED", `Learning from ${doc.filename}`);
      router.push(`/session/${res.sessionId}?topic=${encodeURIComponent(cleanTopic)}`);
    } catch {
      curioToast.error("COULDN'T START DOCUMENT SESSION.");
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleStart();
    }
  };

  return (
    <div className="min-h-screen bg-ice dark:bg-[#070D18] text-navy dark:text-[#F0F4F8] flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Global Navigation */}
      <CurioNav activeRoute="topics" />

      {/* Breadcrumb Sub-bar */}
      <div className="w-full bg-white/70 dark:bg-[#0B1524]/90 border-b border-fog/80 dark:border-[#1E3652] px-6 py-2">
        <div className="max-w-4xl mx-auto flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-navy/60 dark:text-[#829AB1]">
            <Link href="/dashboard" className="hover:text-navy dark:hover:text-white transition-colors">
              DASHBOARD
            </Link>
            <span className="text-fog dark:text-[#2F4D73]">/</span>
            <span className="font-bold text-navy dark:text-[#F0F4F8]">TOPIC SELECTION</span>
          </div>

          <Link
            href="/audio-learning"
            className="hidden sm:inline-flex items-center gap-1.5 text-gap-orange hover:text-gap-orange/80 font-bold transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>TRY AUDIO LEARNING →</span>
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10 md:py-16">
        <div className="text-center max-w-xl mx-auto mb-10">
          <h1 className="font-heading text-3xl md:text-4xl font-extrabold text-navy dark:text-[#F0F4F8] tracking-tight mb-3">
            What do you want to teach?
          </h1>
          <p className="font-sans text-base text-navy/70 dark:text-[#BAC7D5]">
            Enter any concept, algorithm, or idea. Curio will adapt to your explanations.
          </p>
        </div>

        {/* Search Input Box */}
        <div className="bg-white dark:bg-[#0B1524] border-2 border-navy dark:border-[#2F4D73] rounded-[6px] shadow-[0_4px_0_0_#0F2B4A] dark:shadow-[0_4px_0_0_#040910] p-3 flex items-center gap-3 mb-8 transition-all duration-150 focus-within:border-cobalt dark:focus-within:border-cobalt">
          <Search className="w-5 h-5 text-navy/40 dark:text-[#829AB1] ml-2 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter a topic to teach Curio..."
            disabled={loading}
            className="w-full bg-transparent font-sans text-base text-navy dark:text-[#F0F4F8] placeholder:text-navy/40 dark:placeholder:text-[#627D98] focus:outline-none py-1"
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
          <div className="font-mono text-xs uppercase tracking-wider text-navy/50 dark:text-[#829AB1] font-bold mb-3">
            SUGGESTED TOPICS
          </div>
          <div className="flex flex-wrap gap-2.5">
            {suggestedTopics.map((topic) => (
              <button
                key={topic}
                onClick={() => {
                  setQuery(topic);
                }}
                className="font-mono text-xs uppercase font-semibold px-3 py-2 rounded-[4px] bg-white dark:bg-[#101F33] border border-navy dark:border-[#2F4D73] text-navy dark:text-[#F0F4F8] hover:bg-navy dark:hover:bg-cobalt hover:text-white transition-colors select-none shadow-[0_2px_0_0_#0F2B4A] dark:shadow-[0_2px_0_0_#040910] cursor-pointer"
              >
                {topic}
              </button>
            ))}
          </div>
        </div>

        {/* Document Grounding Option */}
        <div className="mb-14 bg-white/70 dark:bg-[#0B1524]/90 border border-slate-200/90 dark:border-[#1E3652] rounded-[8px] p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-navy/70 dark:text-[#BAC7D5] font-bold">
              <FileText className="w-4 h-4 text-cobalt" />
              <span>OR GROUND IN YOUR UPLOADED DOCUMENTS</span>
            </div>
            <Link
              href="/documents"
              className="font-mono text-xs text-cobalt dark:text-[#4D7CFF] hover:underline uppercase font-semibold"
            >
              MY DOCUMENTS →
            </Link>
          </div>

          {readyDocs.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
              {readyDocs.map((doc) => (
                <div
                  key={doc.document_id}
                  onClick={() => !loading && handleStartFromDocument(doc)}
                  className="group flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-[#1E3652] bg-white dark:bg-[#101F33] hover:border-cobalt dark:hover:border-cobalt hover:shadow-xs transition-all cursor-pointer"
                >
                  <div className="truncate pr-2">
                    <div className="font-heading text-xs font-bold text-navy dark:text-[#F0F4F8] truncate group-hover:text-cobalt dark:group-hover:text-[#4D7CFF] transition-colors">
                      {doc.filename}
                    </div>
                    <div className="font-mono text-[10px] text-slate-500 dark:text-[#829AB1] mt-0.5 flex items-center gap-2">
                      <span>{doc.chunk_count} chunks</span>
                      <span>·</span>
                      <span className="text-emerald-700 dark:text-emerald-400">Ready</span>
                    </div>
                  </div>
                  <Sparkles className="w-3.5 h-3.5 text-slate-300 dark:text-[#2F4D73] group-hover:text-cobalt dark:group-hover:text-[#4D7CFF] shrink-0 transition-colors" />
                </div>
              ))}
            </div>
          ) : (
            <p className="font-sans text-xs text-slate-500 dark:text-[#829AB1] mt-1">
              Upload your lecture notes, textbook chapters, or papers in{" "}
              <Link href="/documents" className="text-cobalt dark:text-[#4D7CFF] font-medium underline">
                My Documents
              </Link>{" "}
              to enable source-grounded Feynman inquiries.
            </p>
          )}
        </div>

        {/* Recent Sessions */}
        {recentSessions.length > 0 && (
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-navy/50 dark:text-[#829AB1] font-bold mb-4 flex items-center justify-between">
              <span>RECENT SESSIONS</span>
              <Link
                href="/history"
                className="font-mono text-xs text-cobalt dark:text-[#4D7CFF] hover:underline uppercase"
              >
                VIEW ALL →
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {recentSessions.map((session) => (
                <div
                  key={session.sessionId}
                  className="bg-white dark:bg-[#0B1524] border border-fog dark:border-[#1E3652] rounded-[6px] p-4 shadow-sm hover:border-cobalt dark:hover:border-cobalt transition-colors flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-1 mb-1">
                      <h4 className="font-heading text-sm font-bold text-navy dark:text-[#F0F4F8] truncate">
                        {session.topicName}
                      </h4>
                      <span className="font-mono text-xs font-bold text-cobalt dark:text-[#4D7CFF] shrink-0">
                        {session.understandingScore}/100
                      </span>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[11px] text-navy/60 dark:text-[#BAC7D5] mb-3">
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

                  <div className="pt-3 border-t border-fog/60 dark:border-[#1E3652] flex items-center justify-between gap-2">
                    <Link
                      href={`/session/${session.sessionId}/report`}
                      className="text-xs font-mono text-navy/70 dark:text-[#BAC7D5] hover:text-navy dark:hover:text-white uppercase font-semibold"
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
