"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { GapReport, ConceptCell, UnderstandingLayer } from "@/types/gapReport";
import {
  getGapReport,
  getSessions,
  evaluateSession,
  SessionSummary,
} from "@/services/gapReportService";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import {
  Inbox,
  PlayCircle,
  RefreshCw,
  Sparkles,
  ArrowRight,
  AlertCircle,
} from "lucide-react";

import GapReportHeader from "./GapReportHeader";
import GapReportSummary from "./GapReportSummary";
import TopicSwitcher from "./TopicSwitcher";
import IsometricKnowledgeMap from "./IsometricKnowledgeMap";
import MapControls from "./MapControls";
import SelectedConceptPanel from "./SelectedConceptPanel";
import ConceptListFallback from "./ConceptListFallback";
import { DiagonalSweepTransition } from "./DiagonalSweepTransition";

export function GapReportPage({
  initialSessionId,
}: {
  initialSessionId?: string;
}) {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();

  const [availableSessions, setAvailableSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>(
    initialSessionId || (params?.sessionId as string) || ""
  );
  const [report, setReport] = useState<GapReport | null>(null);
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(null);
  const [selectedLayer, setSelectedLayer] = useState<UnderstandingLayer | null>(null);
  const [isFocusGaps, setIsFocusGaps] = useState(false);
  const [showLayerLabels, setShowLayerLabels] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData(activeSessionId);
  }, [activeSessionId]);

  // Keyboard shortcut: Escape to deselect active cell/layer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedConceptId(null);
        setSelectedLayer(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  async function loadData(targetSessionId?: string) {
    try {
      setIsLoading(true);
      setError(null);

      // 1. Fetch available sessions from backend
      const sessions = await getSessions();
      setAvailableSessions(sessions);

      if (sessions.length === 0) {
        setReport(null);
        return;
      }

      // 2. Determine target session
      const validSessionId =
        targetSessionId && sessions.some((s) => s.session_id === targetSessionId)
          ? targetSessionId
          : sessions[0].session_id;

      if (validSessionId !== activeSessionId) {
        setActiveSessionId(validSessionId);
      }

      // 3. Fetch report for selected session
      const data = await getGapReport(validSessionId);
      setReport(data);
      setSelectedConceptId(null);
      setSelectedLayer(null);
    } catch (err: any) {
      console.error("Error loading gap report data:", err);
      setError(err?.message || "Failed to load data from the backend.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleTriggerEvaluation(sessionId: string) {
    try {
      setIsEvaluating(true);
      toast({
        title: "EVALUATION STARTED",
        description: "Compiling session evidence and running diagnostic evaluation...",
      });

      const evaluatedReport = await evaluateSession(sessionId);
      if (evaluatedReport) {
        setReport(evaluatedReport);
        setActiveSessionId(sessionId);
        toast({
          title: "REPORT GENERATED",
          description: "Gap Report and Isometric Knowledge Map are ready.",
        });
      } else {
        toast({
          title: "EVALUATION FAILED",
          description: "Could not compile report. Ensure the session has active turns.",
          variant: "destructive",
        });
      }
    } catch (err: any) {
      toast({
        title: "EVALUATION ERROR",
        description: err?.message || "Failed to trigger session evaluation.",
        variant: "destructive",
      });
    } finally {
      setIsEvaluating(false);
    }
  }

  const handleResetView = () => {
    setSelectedConceptId(null);
    setSelectedLayer(null);
    setIsFocusGaps(false);
  };

  const handleToggleFocusGaps = () => {
    setIsFocusGaps(!isFocusGaps);
  };

  const handleShowAll = () => {
    setSelectedConceptId(null);
    setSelectedLayer(null);
    setIsFocusGaps(false);
  };

  if (isLoading && !report) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-ice text-navy">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-navy border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="font-mono text-xs font-bold uppercase tracking-wider text-navy/70">
            FETCHING BACKEND GAP REPORT DATA...
          </p>
        </div>
      </div>
    );
  }

  // NO DATA PRESENT STATE (Dedicated Empty State)
  if (!report) {
    const selectedSession = availableSessions.find((s) => s.session_id === activeSessionId);

    return (
      <div className="flex flex-col min-h-screen bg-ice text-navy">
        <DiagonalSweepTransition />
        <GapReportHeader
          topicName="Gap Report"
          onBack={() => {
            if (typeof window !== "undefined" && window.history.length > 1) {
              router.back();
            } else {
              router.push("/");
            }
          }}
        />

        <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-2xl mx-auto w-full text-center">
          <div className="bg-white border-2 border-navy rounded-xl p-8 shadow-[6px_6px_0_0_#0F2B4A] w-full space-y-6">
            {/* Status Pill */}
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-ice border border-navy/20 rounded-full text-[11px] font-mono font-bold tracking-wider text-navy">
              <span className="w-2 h-2 rounded-full bg-gapOrange animate-pulse" />
              STATUS: NO REPORT DATA PRESENT
            </div>

            {/* Icon */}
            <div className="w-16 h-16 mx-auto bg-ice border-2 border-navy rounded-xl flex items-center justify-center shadow-[3px_3px_0_0_#0F2B4A]">
              <Inbox className="w-8 h-8 text-navy" />
            </div>

            {/* Heading & Explanation */}
            <div className="space-y-2">
              <h2 className="font-sora text-2xl font-black uppercase tracking-tight text-navy">
                NO GAP REPORT DATA FOUND
              </h2>
              <p className="font-mono text-xs text-navy/70 leading-relaxed max-w-md mx-auto">
                {availableSessions.length === 0
                  ? "There are currently no learning sessions or evaluations recorded in the backend database. Complete a learning session first to generate your Gap Report and Isometric Knowledge Map."
                  : `Session "${selectedSession?.topic || activeSessionId}" has not been evaluated yet. You can trigger an evaluation below to compile its report.`}
              </p>
            </div>

            {/* Unevaluated Sessions List (if any exist) */}
            {availableSessions.length > 0 && (
              <div className="text-left border border-navy/20 rounded-lg p-4 bg-ice/50 space-y-3">
                <p className="font-mono text-[11px] font-bold uppercase text-navy/70 tracking-wider">
                  AVAILABLE BACKEND SESSIONS ({availableSessions.length})
                </p>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {availableSessions.map((session) => (
                    <div
                      key={session.session_id}
                      className="flex items-center justify-between p-2.5 bg-white border border-navy/20 rounded-[6px] text-xs font-mono"
                    >
                      <div>
                        <p className="font-bold text-navy uppercase">{session.topic}</p>
                        <p className="text-[10px] text-navy/60">
                          ID: {session.session_id.slice(0, 8)}... | Status: {session.status}
                        </p>
                      </div>
                      <button
                        onClick={() => handleTriggerEvaluation(session.session_id)}
                        disabled={isEvaluating}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-cobalt text-white font-mono text-[11px] font-bold rounded-[4px] shadow-[2px_2px_0_0_#0F2B4A] hover:bg-cobalt/90 disabled:opacity-50"
                      >
                        {isEvaluating ? (
                          <RefreshCw className="w-3 h-3 animate-spin" />
                        ) : (
                          <Sparkles className="w-3 h-3" />
                        )}
                        EVALUATE
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <button
                onClick={() => router.push("/")}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-navy text-white font-mono text-xs font-bold uppercase rounded-[6px] shadow-[3px_3px_0_0_#0F2B4A] hover:bg-navy/90 transition-all active:translate-x-[1px] active:translate-y-[1px]"
              >
                <PlayCircle className="w-4 h-4" />
                START LEARNING SESSION
              </button>
              <button
                onClick={() => loadData(activeSessionId)}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 bg-white border border-navy text-navy font-mono text-xs font-bold uppercase rounded-[6px] shadow-[3px_3px_0_0_#0F2B4A] hover:bg-ice transition-all active:translate-x-[1px] active:translate-y-[1px]"
              >
                <RefreshCw className="w-4 h-4" />
                REFRESH DATA
              </button>
            </div>
          </div>
        </div>

        <Toaster />
      </div>
    );
  }

  const selectedConcept = report.concepts.find((c) => c.id === selectedConceptId);
  const selectedGap = report.gaps.find(
    (g) => g.conceptId === selectedConceptId
  );

  return (
    <div className="flex flex-col min-h-screen bg-ice text-navy overflow-x-hidden">
      {/* Diagonal Sweep Page Transition Overlay */}
      <DiagonalSweepTransition />

      {/* Header */}
      <GapReportHeader
        topicName={report.topicName}
        onBack={() => {
          if (typeof window !== "undefined" && window.history.length > 1) {
            router.back();
          } else {
            router.push("/");
          }
        }}
      />

      {/* Main Content Layout */}
      <div className="flex-1 flex flex-col p-4 md:p-6 gap-4 max-w-[1600px] w-full mx-auto">
        {/* Topic Switcher Strip */}
        {report.availableTopics.length > 1 && (
          <TopicSwitcher
            topics={report.availableTopics}
            activeTopicId={activeSessionId}
            onTopicChange={(sessionId) => setActiveSessionId(sessionId)}
          />
        )}

        {/* Summary Stat Cards */}
        <GapReportSummary report={report} />

        {/* Workspace: Isometric Knowledge Map (65%) + Selected Concept Panel (35%) */}
        <div className="flex-1 flex flex-col lg:flex-row gap-5 min-h-[520px]">
          {/* Left Column: Isometric Map & Controls */}
          <div className="flex-1 flex flex-col min-w-0 bg-white border border-navy/20 rounded-xl p-4 md:p-5 shadow-sm">
            <div className="flex-1 flex items-center justify-center overflow-hidden">
              <AnimatePresence mode="wait">
                <motion.div
                  key={report.sessionId}
                  initial={{ opacity: 0, x: 60 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -60 }}
                  transition={{ duration: 0.35, ease: "easeInOut" }}
                  className="w-full h-full"
                >
                  <IsometricKnowledgeMap
                    report={report}
                    selectedConceptId={selectedConceptId}
                    selectedLayer={selectedLayer}
                    isFocusGaps={isFocusGaps}
                    showLayerLabels={showLayerLabels}
                    onSelectConcept={(concept: ConceptCell) => {
                      setSelectedConceptId(concept.id);
                    }}
                    onSelectLayer={(layer) => {
                      setSelectedLayer(layer);
                    }}
                  />
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Map Controls */}
            <MapControls
              isFocusGaps={isFocusGaps}
              showLayerLabels={showLayerLabels}
              onResetView={handleResetView}
              onToggleFocusGaps={handleToggleFocusGaps}
              onShowAll={handleShowAll}
              onToggleLayerLabels={() => setShowLayerLabels(!showLayerLabels)}
            />

            {/* Accessible Screen Reader Fallback */}
            <ConceptListFallback
              report={report}
              selectedConceptId={selectedConceptId}
              onSelectConcept={(id) => setSelectedConceptId(id)}
            />
          </div>

          {/* Right Column: Detail Panel */}
          <div className="w-full lg:w-[420px] shrink-0 min-h-[500px]">
            <SelectedConceptPanel
              concept={selectedConcept}
              gap={selectedGap}
              onSelectRelated={(conceptId) => setSelectedConceptId(conceptId)}
            />
          </div>
        </div>
      </div>

      {/* Editorial Toaster */}
      <Toaster />
    </div>
  );
}
