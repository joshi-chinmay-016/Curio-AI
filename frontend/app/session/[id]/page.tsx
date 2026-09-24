"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Menu, BookOpen, ChevronLeft } from "lucide-react";
import { useSessionStore } from "@/stores/sessionStore";
import { useSessionWebSocket } from "@/hooks/useSessionWebSocket";
import { SessionSidebar } from "@/components/curio/session/SessionSidebar";
import { ChatThread } from "@/components/curio/session/ChatThread";
import { InputArea } from "@/components/curio/session/InputArea";
import { StatusBar } from "@/components/curio/StatusBar";
import { EvaluatingOverlay } from "@/components/curio/session/EvaluatingOverlay";
import { FinishDialog } from "@/components/curio/session/FinishDialog";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { KeycapButton } from "@/components/curio/KeycapButton";

export default function LearningSessionPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = (params?.id as string) || "session_default";
  const topicParam = searchParams?.get("topic") || undefined;

  const {
    topicName,
    mode,
    messages,
    isThinking,
    currentTurnNumber,
    confidence,
    activeGap,
    initSession,
  } = useSessionStore();

  const { sendMessage, triggerStuck, triggerEndSession } =
    useSessionWebSocket(sessionId);

  const [finishDialogOpen, setFinishDialogOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    initSession(sessionId, topicParam);
  }, [sessionId, topicParam, initSession]);

  const handleConfirmEnd = () => {
    setFinishDialogOpen(false);
    triggerEndSession();
  };

  const isEvaluating = mode === "EVALUATING";

  return (
    <div className="h-screen flex bg-ice text-navy overflow-hidden select-none selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Collapsible Session Sidebar */}
      <SessionSidebar
        activeSessionId={sessionId}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      {/* Central Learning Workspace */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-ice relative">
        {/* Top Header */}
        <header className="w-full bg-white border-b border-fog px-4 md:px-6 py-3 flex items-center justify-between z-30 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {/* Mobile menu trigger */}
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="p-1.5 text-navy/70 hover:text-navy md:hidden"
              aria-label="Open sessions sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>

            <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-navy/40 hidden sm:inline">
              TOPIC:
            </span>
            <h2 className="font-heading text-sm md:text-base font-bold text-navy truncate">
              {topicName || "Learning Session"}
            </h2>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {/* Mode status indicator */}
            {mode === "STUDENT" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[3px] font-mono text-xs font-semibold bg-cobalt/10 text-cobalt border border-cobalt/20">
                <span className="w-2 h-2 rounded-full bg-cobalt animate-pulse" />
                <span className="hidden sm:inline">Student Mode</span>
              </span>
            )}
            {mode === "TEACHER" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[3px] font-mono text-xs font-semibold bg-gap-orange/10 text-gap-orange border border-gap-orange/30">
                <span className="text-xs">◆</span>
                <span className="hidden sm:inline">Teacher Mode</span>
              </span>
            )}
            {mode === "EVALUATING" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[3px] font-mono text-xs font-semibold bg-navy text-white">
                <span className="animate-spin text-xs">◈</span>
                <span className="hidden sm:inline">Evaluating</span>
              </span>
            )}

            <KeycapButton
              variant="ghost"
              size="sm"
              onClick={() => setFinishDialogOpen(true)}
              className="text-[11px]"
            >
              END SESSION
            </KeycapButton>
          </div>
        </header>

        {/* Chat Thread */}
        <div
          className={`flex-1 overflow-hidden flex flex-col transition-opacity duration-300 ${
            isEvaluating ? "opacity-40 pointer-events-none" : "opacity-100"
          }`}
        >
          <ChatThread
            messages={messages}
            isThinking={isThinking}
            activeGap={activeGap}
          />
        </div>

        {/* Subtle Status Bar */}
        <div className="shrink-0 z-20">
          <StatusBar
            mode={mode}
            turnNumber={currentTurnNumber}
            confidence={confidence}
            activeGapTitle={activeGap?.title}
            onStuckClick={triggerStuck}
          />
        </div>

        {/* Pinned Message Composer */}
        <div
          className={`shrink-0 z-20 bg-ice transition-opacity duration-300 ${
            isEvaluating ? "opacity-40 pointer-events-none" : "opacity-100"
          }`}
        >
          <InputArea
            mode={mode}
            onSendMessage={sendMessage}
            onStuck={triggerStuck}
            onFinishSession={() => setFinishDialogOpen(true)}
            disabled={isEvaluating}
          />
        </div>

        {/* Evaluating Overlay */}
        {isEvaluating && <EvaluatingOverlay turnCount={currentTurnNumber} />}

        {/* Finish Session Confirm Dialog */}
        <FinishDialog
          isOpen={finishDialogOpen}
          onCancel={() => setFinishDialogOpen(false)}
          onConfirm={handleConfirmEnd}
        />
      </main>
    </div>
  );
}
