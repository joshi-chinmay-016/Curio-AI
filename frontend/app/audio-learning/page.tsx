"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Volume2,
  Mic,
  Sparkles,
  BookOpen,
  GraduationCap,
  Layers,
  RotateCcw,
  Menu,
  X,
  ExternalLink,
  Clock,
  Loader2,
} from "lucide-react";
import { ProtectedRoute } from "@/components/curio/auth/ProtectedRoute";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { CharacterStage } from "@/components/curio/audio/CharacterStage";
import { AudioControls } from "@/components/curio/audio/AudioControls";
import { AudioSessionSetup } from "@/components/curio/audio/AudioSessionSetup";
import { AudioSessionSummary } from "@/components/curio/audio/AudioSessionSummary";
import { SessionSidebar } from "@/components/curio/session/SessionSidebar";
import {
  AudioLearningMode,
  AudioSessionConfig,
  CharacterAnimationState,
  CharacterType,
} from "@/types/audioLearning";
import { SessionSummary } from "@/types/history";
import { speechService, sanitizeTextForSpeech } from "@/services/speechService";
import { getSessionRepository, StoredSession } from "@/services/sessionRepository";
import { curioToast } from "@/components/curio/CurioToast";

import { useAudioCharacterSync } from "@/hooks/useAudioCharacterSync";

export default function AudioLearningPage() {
  return (
    <ProtectedRoute>
      <AudioLearningStage />
    </ProtectedRoute>
  );
}

function AudioLearningStage() {
  const router = useRouter();

  // Session lifecycle states: "setup" | "conversation" | "summary"
  const [sessionPhase, setSessionPhase] = useState<"setup" | "conversation" | "summary">("setup");
  const [sessionId, setSessionId] = useState<string>("");
  const [mode, setMode] = useState<AudioLearningMode>("STUDENT");
  const [topic, setTopic] = useState<string>("");
  const [activeConcept, setActiveConcept] = useState<string>("");
  const [documentId, setDocumentId] = useState<string | undefined>();
  const [documentName, setDocumentName] = useState<string | undefined>();

  // Collapsible sidebar & mobile drawer state
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);

  // Selected previous session modal/detail view state
  const [viewingSession, setViewingSession] = useState<SessionSummary | null>(null);
  const [sessionDetail, setSessionDetail] = useState<StoredSession | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);

  // Synchronized Character Animation & Audio Lifecycle Controller
  const {
    character,
    animationState,
    isTeacherActive,
    isPlayingSpeech,
    currentSpeechText,
    spokenCharIndex,
    setSessionId: syncSetSessionId,
    setMode: syncSetMode,
    setAnimationState,
    handleRecordingStart,
    handleRecordingStop,
    handleTranscriptionStart,
    handleAnswerSubmit,
    handleEvaluationReceived,
    handleProfessorSkip,
    handleSpeechStart,
    handleSpeechBoundary,
    handleSpeechEnd,
    handleSpeechInterrupt,
    resetController,
  } = useAudioCharacterSync({
    initialMode: "STUDENT",
    onInterventionStart: () => {
      curioToast.error(
        "TEACHER INTERVENTION",
        "Ms. Clara has stepped in to clarify a fundamental concept."
      );
    },
    onInterventionEnd: () => {
      curioToast.success("CONCEPT VERIFIED", "Great job! Returning to Leo for inquiry.");
    },
  });

  const [isBusyProcessing, setIsBusyProcessing] = useState<boolean>(false);
  const [isStartingSession, setIsStartingSession] = useState<boolean>(false);

  // Performance Stats
  const [turnIndex, setTurnIndex] = useState<number>(1);
  const [confidence, setConfidence] = useState<number>(65);
  const [consecutiveUnanswered, setConsecutiveUnanswered] = useState<number>(0);
  const [totalQuestions, setTotalQuestions] = useState<number>(0);
  const [totalAnswered, setTotalAnswered] = useState<number>(0);
  const [totalSkipped, setTotalSkipped] = useState<number>(0);
  const [hasEndedByProfessor, setHasEndedByProfessor] = useState<boolean>(false);
  const [strengths, setStrengths] = useState<string[]>([]);
  const [gaps, setGaps] = useState<string[]>([]);

  const isMountedRef = useRef<boolean>(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      speechService.stop();
    };
  }, []);

  // Speak AI response aloud through speechService and synchronize character animation and live captions
  const speakAloud = useCallback(
    (text: string, onDone?: () => void) => {
      const cleanSpeech = sanitizeTextForSpeech(text);
      if (!cleanSpeech) {
        onDone?.();
        return;
      }

      handleSpeechStart(cleanSpeech);
      const msgId = "audio_msg_" + Date.now();

      speechService.speak(msgId, cleanSpeech, {
        onStart: () => {
          if (isMountedRef.current) {
            handleSpeechStart(cleanSpeech);
          }
        },
        onBoundary: (charIndex) => {
          if (isMountedRef.current) {
            handleSpeechBoundary(charIndex);
          }
        },
        onEnd: () => {
          if (isMountedRef.current) {
            handleSpeechEnd();
            onDone?.();
          }
        },
        onError: () => {
          if (isMountedRef.current) {
            handleSpeechInterrupt();
            onDone?.();
          }
        },
      });
    },
    [handleSpeechStart, handleSpeechBoundary, handleSpeechEnd, handleSpeechInterrupt]
  );

  // 1. Session Setup and Start
  const handleStartSession = async (config: AudioSessionConfig) => {
    setIsStartingSession(true);
    try {
      const repo = getSessionRepository();
      const newSession = await repo.createSession(
        config.topic,
        config.sourceType,
        config.documentId
      );

      const createdId = newSession.sessionId;
      syncSetSessionId(createdId);
      syncSetMode(config.mode);
      setSessionId(createdId);
      setMode(config.mode);
      setTopic(config.topic);
      setDocumentId(config.documentId);
      setDocumentName(config.documentName);
      setConsecutiveUnanswered(0);
      setTotalQuestions(1);
      setTotalAnswered(0);
      setTotalSkipped(0);
      setHasEndedByProfessor(false);
      setTurnIndex(1);

      if (config.mode === "STUDENT") {
        const initialGreeting = `Hi! I'm Leo. Can you teach me about ${config.topic}? What is it in simple terms, and why does it matter?`;
        setActiveConcept(config.topic);
        setSessionPhase("conversation");

        // Speak student greeting aloud automatically
        setTimeout(() => {
          speakAloud(initialGreeting);
        }, 350);
      } else {
        // Professor Mode
        const initialQuestion = `Welcome to the examination on ${config.topic}. Let us begin with the core invariants. Can you clearly state the fundamental mechanism of ${config.topic} and provide a concrete example?`;
        setActiveConcept(config.topic);
        setSessionPhase("conversation");

        // Speak professor's question aloud automatically
        setTimeout(() => {
          speakAloud(initialQuestion);
        }, 350);
      }
    } catch (err: any) {
      console.error("Failed to start audio session:", err);
      curioToast.error("INITIALIZATION FAILED", err.message || "Could not start audio session.");
    } finally {
      setIsStartingSession(false);
    }
  };

  // 2. User Speaks Answer (Audio is captured and auto-submitted directly to API)
  const handleSendAnswer = async (spokenText: string) => {
    if (!spokenText.trim() || isBusyProcessing) return;

    speechService.stop();
    setIsBusyProcessing(true);
    handleAnswerSubmit(mode);

    try {
      const repo = getSessionRepository();

      // Ensure note-taking / marking animation is visibly performed for at least 1.4s
      const [turnResult] = await Promise.all([
        repo.sendMessage(sessionId, spokenText.trim(), "VOICE"),
        new Promise((resolve) => setTimeout(resolve, 1400)),
      ]);

      setIsBusyProcessing(false);

      if (turnResult.evaluation) {
        setConfidence(Math.round(turnResult.decision.confidence));
        if (turnResult.evaluation.mastered_concepts?.length) {
          setStrengths((prev) => Array.from(new Set([...prev, ...turnResult.evaluation.mastered_concepts])));
        }
        if (turnResult.evaluation.misconceptions?.length) {
          setGaps((prev) => Array.from(new Set([...prev, ...turnResult.evaluation.misconceptions])));
        }
      }

      const nextMode = turnResult.decision.next_mode;
      const aiContent = turnResult.ai_message.content;
      const correctness = turnResult.evaluation?.correctness ?? 0.7;
      setTotalQuestions((prev) => prev + 1);
      setTotalAnswered((prev) => prev + 1);
      setTurnIndex((prev) => prev + 1);

      if (mode === "PROFESSOR") {
        setConsecutiveUnanswered(0);
      }

      handleEvaluationReceived(
        mode,
        nextMode,
        turnResult.decision.should_restore_interrupted_question,
        correctness
      );

      // Show reaction before beginning speech
      setTimeout(() => {
        speakAloud(aiContent);
      }, 600);
    } catch (err: any) {
      console.error("Message submission error:", err);
      setIsBusyProcessing(false);
      setAnimationState("error");
      curioToast.error("SUBMISSION ERROR", "Network error. Please tap the mic to try again.");
    }
  };

  // 3. Skip Question (Professor Mode specific)
  const handleSkipQuestion = async () => {
    if (isBusyProcessing) return;
    speechService.stop();

    const nextUnanswered = consecutiveUnanswered + 1;
    setConsecutiveUnanswered(nextUnanswered);
    setTotalSkipped((prev) => prev + 1);
    setTotalQuestions((prev) => prev + 1);
    setTurnIndex((prev) => prev + 1);

    handleProfessorSkip(nextUnanswered);

    // Check 3 strikes consecutive unanswered policy
    if (nextUnanswered >= 3) {
      setHasEndedByProfessor(true);

      const closingRemarks =
        "Three consecutive unanswered questions demonstrate that we have reached the limit of current preparation. I am concluding this examination now. Review your core concepts before testing again.";

      speakAloud(closingRemarks, () => {
        // After speech finishes, animate professor leaving and show summary
        setAnimationState("leaving");
        setTimeout(() => {
          setSessionPhase("summary");
        }, 1200);
      });
      return;
    }

    // Professor moves on to next question
    setIsBusyProcessing(true);

    try {
      const repo = getSessionRepository();
      const turnResult = await repo.sendMessage(
        sessionId,
        "I do not know the answer to this question. Please move on to the next question.",
        "VOICE"
      );

      setIsBusyProcessing(false);
      const aiContent = turnResult.ai_message.content;

      // Speak next question aloud automatically
      speakAloud(aiContent);
    } catch (err: any) {
      setIsBusyProcessing(false);
      curioToast.error("ERROR", "Could not advance to next question.");
    }
  };

  // Explicit End Session
  const handleEndSession = async () => {
    speechService.stop();
    resetController(mode);
    try {
      const repo = getSessionRepository();
      await repo.endSession(sessionId);
    } catch (err) {
      console.warn("End session call completed with notice:", err);
    }
    setSessionPhase("summary");
  };

  // Start a fresh Audio Session configuration
  const handleNewAudioSession = () => {
    if (sessionPhase === "conversation") {
      const confirmLeave = window.confirm(
        "You have an ongoing audio session. Are you sure you want to start a new session configuration?"
      );
      if (!confirmLeave) return;
    }
    speechService.stop();
    resetController("STUDENT");
    setSessionPhase("setup");
    setSessionId("");
    setTopic("");
    setConfidence(65);
    setTurnIndex(1);
    setTotalQuestions(0);
    setTotalAnswered(0);
    setTotalSkipped(0);
    setHasEndedByProfessor(false);
  };

  // Select a previous session to review in modal
  const handleSelectPreviousSession = async (session: SessionSummary) => {
    setViewingSession(session);
    setSessionDetail(null);
    setIsLoadingDetail(true);
    try {
      const repo = getSessionRepository();
      const detailed = await repo.getSession(session.sessionId);
      setSessionDetail(detailed);
    } catch (err) {
      console.warn("Could not load session detail:", err);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Preload selected previous topic into Audio Session setup
  const handlePracticeTopicFromPreviousSession = (topicName: string) => {
    if (sessionPhase === "conversation") {
      const confirmLeave = window.confirm(
        "You have an ongoing audio session. Are you sure you want to configure a new session for this topic?"
      );
      if (!confirmLeave) return;
    }
    speechService.stop();
    resetController("STUDENT");
    setSessionPhase("setup");
    setSessionId("");
    setTopic(topicName);
    setConfidence(65);
    setTurnIndex(1);
    setTotalQuestions(0);
    setTotalAnswered(0);
    setTotalSkipped(0);
    setHasEndedByProfessor(false);
    setViewingSession(null);
    curioToast.success("TOPIC LOADED", `Ready to practice "${topicName}" with voice!`);
  };

  return (
    <div className="h-screen flex bg-ice text-navy overflow-hidden selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Collapsible Session History Sidebar */}
      <SessionSidebar
        activeSessionId={sessionId}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
        onNewSession={handleNewAudioSession}
        newSessionLabel="NEW AUDIO SESSION"
        onSelectSession={handleSelectPreviousSession}
      />

      {/* Central Audio Learning Workspace */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-ice relative">
        {/* Header Bar */}
        <header className="w-full bg-white border-b border-fog px-4 md:px-6 py-3 sticky top-0 z-30 shadow-xs shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Mobile menu trigger */}
              <button
                onClick={() => setMobileSidebarOpen(true)}
                className="p-1.5 text-navy/70 hover:text-navy hover:bg-ice rounded-[4px] md:hidden cursor-pointer"
                aria-label="Open sessions sidebar"
                title="Open previous sessions"
              >
                <Menu className="w-5 h-5" />
              </button>

              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-ice hover:bg-ice/80 border border-fog rounded-[6px] font-mono text-xs font-bold text-navy/70 hover:text-navy transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">DASHBOARD</span>
              </Link>

              <Link
                href="/"
                className="font-mono text-xl font-bold tracking-wider text-navy hover:text-cobalt transition-colors"
              >
                CURIO<span className="text-gap-orange">.</span>
              </Link>

              {sessionPhase === "conversation" ? (
                <div className="hidden md:flex items-center gap-2 pl-3 border-l border-fog">
                  <span className="font-mono text-[10px] uppercase font-bold text-navy/40">
                    TOPIC:
                  </span>
                  <span className="font-heading text-xs font-bold text-navy truncate max-w-[200px]">
                    {topic}
                  </span>
                </div>
              ) : (
                <nav className="hidden lg:flex items-center gap-4 text-xs font-mono font-semibold uppercase text-navy/70 pl-2">
                  <Link href="/dashboard" className="hover:text-navy transition-colors">
                    DASHBOARD
                  </Link>
                  <Link href="/topics" className="hover:text-navy transition-colors">
                    TOPICS
                  </Link>
                  <Link href="/documents" className="hover:text-navy transition-colors">
                    DOCUMENTS
                  </Link>
                  <Link href="/history" className="hover:text-navy transition-colors">
                    HISTORY
                  </Link>
                  <Link href="/characters" className="hover:text-navy transition-colors">
                    CHARACTERS
                  </Link>
                </nav>
              )}
            </div>

            {/* Mode Pill & End Session */}
            <div className="flex items-center gap-3">
              {sessionPhase === "conversation" && (
                <>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-ice border border-fog rounded-full">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        isTeacherActive
                          ? "bg-gap-orange animate-pulse"
                          : mode === "PROFESSOR"
                          ? "bg-navy"
                          : "bg-cobalt"
                      }`}
                    />
                    <span className="font-mono text-[11px] font-bold text-navy uppercase">
                      {isTeacherActive
                        ? "TEACHER INTERVENTION"
                        : mode === "PROFESSOR"
                        ? "PROFESSOR MODE"
                        : "STUDENT MODE"}
                    </span>
                    <span className="font-mono text-[10px] text-navy/40">·</span>
                    <span className="font-mono text-[10px] uppercase font-semibold text-navy/60">
                      Turn {turnIndex}
                    </span>
                  </div>

                  <button
                    onClick={handleEndSession}
                    className="px-3 py-1.5 text-xs font-mono font-bold uppercase text-navy/60 hover:text-rose-600 border border-fog hover:bg-rose-50 rounded-[6px] transition-colors cursor-pointer"
                  >
                    FINISH SESSION
                  </button>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Main Page Area */}
        <main className="flex-1 overflow-y-auto px-4 py-6 md:py-10 flex flex-col items-center justify-center">
          <div className="max-w-4xl w-full mx-auto my-auto">
            {sessionPhase === "setup" && (
              <AudioSessionSetup
                onStartSession={handleStartSession}
                isStarting={isStartingSession}
              />
            )}

            {sessionPhase === "conversation" && (
              <div className="w-full flex flex-col items-center gap-6">
                {/* Central Animated Character Stage with Live Captions for AI Spoken Dialogue */}
                <CharacterStage
                  character={character}
                  animationState={animationState}
                  activeConcept={activeConcept}
                  isTeacherIntervention={isTeacherActive}
                  isPlayingSpeech={isPlayingSpeech}
                  captionText={isPlayingSpeech ? currentSpeechText : ""}
                  spokenCharIndex={spokenCharIndex}
                  onReplaySpeech={() => speakAloud(currentSpeechText)}
                  onStopSpeech={() => speechService.stop()}
                />

                {/* Speech-to-Speech Audio Controls (No Transcript Input) */}
                <AudioControls
                  onSendAnswer={handleSendAnswer}
                  onSkipQuestion={mode === "PROFESSOR" ? handleSkipQuestion : undefined}
                  isBusyProcessing={isBusyProcessing}
                  isPlayingSpeech={isPlayingSpeech}
                  isProfessorMode={mode === "PROFESSOR"}
                  onRecordingStateChange={(rec) => {
                    if (rec) handleRecordingStart();
                    else handleRecordingStop();
                  }}
                  onTranscribingStateChange={(trans) => {
                    if (trans) handleTranscriptionStart();
                  }}
                />
              </div>
            )}

            {sessionPhase === "summary" && (
              <AudioSessionSummary
                sessionId={sessionId}
                topic={topic}
                mode={mode}
                understandingScore={confidence}
                totalQuestions={totalQuestions}
                totalAnswered={totalAnswered}
                totalSkipped={totalSkipped}
                consecutiveUnanswered={consecutiveUnanswered}
                hasEndedByProfessor={hasEndedByProfessor}
                strengths={strengths}
                gaps={gaps}
                onRestartSession={() => {
                  resetController("STUDENT");
                  setSessionPhase("setup");
                }}
              />
            )}
          </div>
        </main>
      </div>

      {/* Previous Session Detail & Review Modal */}
      {viewingSession && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy/60 backdrop-blur-xs animate-fade-in"
          onClick={() => setViewingSession(null)}
        >
          <div
            className="bg-white border-2 border-navy rounded-[10px] shadow-[8px_8px_0_0_#0F2B4A] w-full max-w-xl max-h-[90vh] flex flex-col overflow-hidden text-navy"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-4 md:p-5 border-b border-fog flex items-center justify-between bg-ice/40 shrink-0">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-gap-orange" />
                <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-navy/60">
                  PREVIOUS SESSION OVERVIEW
                </span>
              </div>
              <button
                onClick={() => setViewingSession(null)}
                className="p-1.5 text-navy/50 hover:text-navy hover:bg-fog/30 rounded-[4px] transition-colors cursor-pointer"
                title="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-5 md:p-6 overflow-y-auto space-y-5">
              <div>
                <h3 className="font-heading text-xl md:text-2xl font-extrabold text-navy leading-tight">
                  {viewingSession.topicName}
                </h3>
                <div className="flex items-center gap-2 mt-1.5 text-xs font-mono text-navy/60">
                  <Clock className="w-3.5 h-3.5 text-navy/40" />
                  <span>
                    {new Date(viewingSession.createdAt).toLocaleDateString([], {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  <span>·</span>
                  <span
                    className={`px-2 py-0.5 rounded-[3px] text-[10px] font-bold uppercase ${
                      viewingSession.status === "COMPLETED"
                        ? "bg-emerald-50 text-emerald-800 border border-emerald-300"
                        : "bg-amber-50 text-amber-800 border border-amber-300"
                    }`}
                  >
                    {viewingSession.status}
                  </span>
                </div>
              </div>

              {/* Stats Bar */}
              <div className="grid grid-cols-3 gap-2.5">
                <div className="bg-ice/50 border border-fog rounded-[6px] p-2.5 text-center">
                  <span className="font-mono text-[10px] uppercase font-bold text-navy/40 block">Score</span>
                  <span className="font-mono text-lg font-extrabold text-navy">
                    {viewingSession.understandingScore}%
                  </span>
                </div>
                <div className="bg-ice/50 border border-fog rounded-[6px] p-2.5 text-center">
                  <span className="font-mono text-[10px] uppercase font-bold text-navy/40 block">Turns</span>
                  <span className="font-mono text-lg font-extrabold text-navy">
                    {viewingSession.turnCount}
                  </span>
                </div>
                <div className="bg-ice/50 border border-fog rounded-[6px] p-2.5 text-center">
                  <span className="font-mono text-[10px] uppercase font-bold text-navy/40 block">Mastery</span>
                  <span className="font-mono text-xs font-bold text-cobalt block mt-1">
                    {viewingSession.masteryLevel || "Developing"}
                  </span>
                </div>
              </div>

              {/* Dialogue History / Messages Preview */}
              <div>
                <label className="font-mono text-xs uppercase font-bold text-navy/60 block mb-2 tracking-wider">
                  SESSION DIALOGUE EXCERPT
                </label>
                {isLoadingDetail ? (
                  <div className="flex items-center justify-center p-8 bg-ice/30 border border-fog rounded-[6px] text-xs font-mono text-navy/50 gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-cobalt" />
                    <span>Loading dialogue transcript...</span>
                  </div>
                ) : sessionDetail?.messages && sessionDetail.messages.length > 0 ? (
                  <div className="max-h-56 overflow-y-auto space-y-2 p-3 bg-ice/40 border border-fog rounded-[6px]">
                    {sessionDetail.messages.map((m, idx) => (
                      <div
                        key={idx}
                        className={`p-2.5 rounded-[4px] text-xs leading-relaxed ${
                          m.sender === "USER"
                            ? "bg-white border border-fog/80 text-navy"
                            : "bg-navy text-white"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1 text-[10px] font-mono font-bold uppercase opacity-70">
                          <span>{m.sender === "USER" ? "Your Spoken Answer" : "AI Companion"}</span>
                          {m.inputType && <span>{m.inputType}</span>}
                        </div>
                        <p className="font-sans line-clamp-3">{m.content}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-ice/30 border border-fog rounded-[6px] text-center font-mono text-xs text-navy/50">
                    No transcript messages recorded for this session.
                  </div>
                )}
              </div>
            </div>

            {/* Modal Actions */}
            <div className="p-4 border-t border-fog bg-ice/30 flex flex-wrap items-center justify-between gap-2.5 shrink-0">
              <button
                type="button"
                onClick={() => handlePracticeTopicFromPreviousSession(viewingSession.topicName)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-gap-orange hover:bg-gap-orange/90 text-white font-mono text-xs font-bold uppercase rounded-[4px] shadow-[0_2px_0_0_#C24E05] hover:shadow-none transition-all cursor-pointer"
              >
                <Mic className="w-3.5 h-3.5" />
                PRACTICE THIS TOPIC IN AUDIO
              </button>

              <div className="flex items-center gap-2">
                <Link
                  href={`/session/${viewingSession.sessionId}?topic=${encodeURIComponent(viewingSession.topicName)}`}
                  className="inline-flex items-center gap-1 px-3 py-2 bg-white hover:bg-ice border border-fog rounded-[4px] font-mono text-xs font-bold text-navy transition-colors cursor-pointer"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-cobalt" />
                  FULL CHAT
                </Link>

                <Link
                  href={`/session/${viewingSession.sessionId}/report`}
                  className="inline-flex items-center gap-1 px-3 py-2 bg-navy hover:bg-[#183d66] text-white rounded-[4px] font-mono text-xs font-bold transition-colors cursor-pointer"
                >
                  <BookOpen className="w-3.5 h-3.5 text-gap-orange" />
                  GAP REPORT
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
