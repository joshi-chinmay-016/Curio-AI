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
} from "lucide-react";
import { ProtectedRoute } from "@/components/curio/auth/ProtectedRoute";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { CharacterStage } from "@/components/curio/audio/CharacterStage";
import { AudioControls } from "@/components/curio/audio/AudioControls";
import { AudioSessionSetup } from "@/components/curio/audio/AudioSessionSetup";
import { AudioSessionSummary } from "@/components/curio/audio/AudioSessionSummary";
import {
  AudioLearningMode,
  AudioSessionConfig,
  CharacterAnimationState,
  CharacterType,
} from "@/types/audioLearning";
import { speechService, sanitizeTextForSpeech } from "@/services/speechService";
import { getSessionRepository } from "@/services/sessionRepository";
import { curioToast } from "@/components/curio/CurioToast";

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

  // Character state
  const [character, setCharacter] = useState<CharacterType>("student");
  const [animationState, setAnimationState] = useState<CharacterAnimationState>("idle");
  const [isTeacherActive, setIsTeacherActive] = useState<boolean>(false);

  // Audio & Speech State
  const [currentSpeechText, setCurrentSpeechText] = useState<string>("");
  const [isPlayingSpeech, setIsPlayingSpeech] = useState<boolean>(false);
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

  // Subscribe to speech playback state
  useEffect(() => {
    const unsubscribe = speechService.subscribe((state) => {
      if (!isMountedRef.current) return;
      setIsPlayingSpeech(state.isPlaying);
      if (state.isPlaying) {
        setAnimationState("speaking");
      } else if (animationState === "speaking") {
        setAnimationState("idle");
      }
    });
    return () => unsubscribe();
  }, [animationState]);

  // Speak AI response aloud through speechService and synchronize character animation
  const speakAloud = useCallback((text: string, onDone?: () => void) => {
    const cleanSpeech = sanitizeTextForSpeech(text);
    if (!cleanSpeech) {
      onDone?.();
      return;
    }

    setCurrentSpeechText(cleanSpeech);
    setAnimationState("speaking");
    const msgId = "audio_msg_" + Date.now();

    speechService.speak(msgId, cleanSpeech, {
      onStart: () => {
        if (isMountedRef.current) {
          setIsPlayingSpeech(true);
          setAnimationState("speaking");
        }
      },
      onEnd: () => {
        if (isMountedRef.current) {
          setIsPlayingSpeech(false);
          setAnimationState("idle");
          onDone?.();
        }
      },
      onError: () => {
        if (isMountedRef.current) {
          setIsPlayingSpeech(false);
          setAnimationState("idle");
          onDone?.();
        }
      },
    });
  }, []);

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
        setCharacter("student");
        setIsTeacherActive(false);

        const initialGreeting = `Hi! I'm Leo. Can you teach me about ${config.topic}? What is it in simple terms, and why does it matter?`;
        setActiveConcept(config.topic);
        setSessionPhase("conversation");

        // Speak student greeting aloud automatically
        setTimeout(() => {
          speakAloud(initialGreeting);
        }, 350);
      } else {
        // Professor Mode
        setCharacter("professor");
        setIsTeacherActive(false);

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

  // 2. User Speaks Answer (Speech recognition auto-submits directly to API)
  const handleSendAnswer = async (spokenText: string) => {
    if (!spokenText.trim() || isBusyProcessing) return;

    speechService.stop();
    setIsBusyProcessing(true);
    setAnimationState("taking_notes");

    try {
      // Simulate student thinking / professor evaluating
      setAnimationState("thinking");

      const repo = getSessionRepository();
      const turnResult = await repo.sendMessage(sessionId, spokenText.trim(), "VOICE");

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
      setTotalQuestions((prev) => prev + 1);
      setTotalAnswered((prev) => prev + 1);
      setTurnIndex((prev) => prev + 1);

      // Student Mode logic
      if (mode === "STUDENT") {
        // Teacher Intervention triggered
        if (nextMode === "TEACHER" && !isTeacherActive) {
          setIsTeacherActive(true);
          setCharacter("teacher");
          setAnimationState("teacher_transition");
          curioToast.error(
            "TEACHER INTERVENTION",
            "Ms. Clara has stepped in to clarify a fundamental concept."
          );

          // Speak teacher explanation aloud automatically
          speakAloud(aiContent);
          return;
        }

        // Return from Teacher to Student
        if (turnResult.decision.should_restore_interrupted_question && isTeacherActive) {
          setIsTeacherActive(false);
          setCharacter("student");
          setAnimationState("impressed");
          curioToast.success("CONCEPT VERIFIED", "Great job! Returning to Leo for inquiry.");

          // Speak restored question aloud automatically
          speakAloud(aiContent);
          return;
        }

        // Continuing in current character
        const correctness = turnResult.evaluation?.correctness ?? 0.7;
        if (correctness >= 0.8) {
          setAnimationState("impressed");
        } else if (correctness < 0.5) {
          setAnimationState("confused");
        } else {
          setAnimationState("curious");
        }

        // Speak follow-up question aloud automatically
        speakAloud(aiContent);
      } else {
        // Professor Mode logic
        const correctness = turnResult.evaluation?.correctness ?? 0.5;

        // Reset consecutive unanswered on genuine answer
        setConsecutiveUnanswered(0);

        if (correctness >= 0.8) {
          setAnimationState("impressed"); // Professor approving nod
        } else if (correctness < 0.4) {
          setAnimationState("skeptical");
        } else {
          setAnimationState("idle");
        }

        // Speak professor's next question aloud automatically
        speakAloud(aiContent);
      }
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

    // Check 3 strikes consecutive unanswered policy
    if (nextUnanswered >= 3) {
      setHasEndedByProfessor(true);
      setAnimationState("grumpy");

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
    setAnimationState("skeptical");
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
    try {
      const repo = getSessionRepository();
      await repo.endSession(sessionId);
    } catch (err) {
      console.warn("End session call completed with notice:", err);
    }
    setSessionPhase("summary");
  };

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Header Bar */}
      <header className="w-full bg-white border-b border-fog px-6 py-4 sticky top-0 z-30 shadow-xs">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
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

            {sessionPhase === "conversation" && (
              <div className="hidden md:flex items-center gap-2 pl-3 border-l border-fog">
                <span className="font-mono text-[10px] uppercase font-bold text-navy/40">
                  TOPIC:
                </span>
                <span className="font-heading text-xs font-bold text-navy truncate max-w-[220px]">
                  {topic}
                </span>
              </div>
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
      <main className="max-w-4xl w-full mx-auto px-4 py-6 md:py-10 flex-1 flex flex-col items-center justify-center">
        {sessionPhase === "setup" && (
          <AudioSessionSetup
            onStartSession={handleStartSession}
            isStarting={isStartingSession}
          />
        )}

        {sessionPhase === "conversation" && (
          <div className="w-full flex flex-col items-center gap-6">
            {/* Central Animated Character Stage */}
            <CharacterStage
              character={character}
              animationState={animationState}
              activeConcept={activeConcept}
              isTeacherIntervention={isTeacherActive}
              isPlayingSpeech={isPlayingSpeech}
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
                if (rec) setAnimationState("recording");
                else if (animationState === "recording") setAnimationState("idle");
              }}
              onTranscribingStateChange={(trans) => {
                if (trans) setAnimationState("transcribing");
                else if (animationState === "transcribing") setAnimationState("idle");
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
            onRestartSession={() => setSessionPhase("setup")}
          />
        )}
      </main>
    </div>
  );
}
