"use client";

import React from "react";
import {
  CharacterType,
  CharacterAnimationState,
} from "@/types/audioLearning";
import {
  Volume2,
  Mic,
  Brain,
  FileEdit,
  HelpCircle,
  Sparkles,
  AlertCircle,
  BookOpen,
  GraduationCap,
} from "lucide-react";

interface CharacterStageProps {
  character: CharacterType;
  animationState: CharacterAnimationState;
  activeConcept?: string;
  isTeacherIntervention?: boolean;
  isPlayingSpeech?: boolean;
  onStopSpeech?: () => void;
  onReplaySpeech?: () => void;
  statusLabel?: string;
}

export function CharacterStage({
  character,
  animationState,
  activeConcept,
  isTeacherIntervention = false,
  isPlayingSpeech = false,
  onStopSpeech,
  onReplaySpeech,
  statusLabel,
}: CharacterStageProps) {
  // Character metadata and source images
  let imageSrc = "/characters/student.png";
  let characterName = "Leo (Student)";
  let characterRole = "Curious Learner";
  let characterVibe = "Explain concepts simply so Leo understands";
  let themeRing = "border-cobalt/40 shadow-[0_0_40px_rgba(58,99,255,0.25)]";
  let ambientGlow = "from-cobalt/15 via-transparent to-transparent";

  if (character === "teacher") {
    imageSrc = "/characters/teacher.png";
    characterName = "Ms. Clara (Teacher)";
    characterRole = "Pedagogical Guide";
    characterVibe = "Isolating the core invariant to help you recover";
    themeRing = "border-gap-orange/50 shadow-[0_0_40px_rgba(255,107,26,0.3)]";
    ambientGlow = "from-gap-orange/20 via-transparent to-transparent";
  } else if (character === "professor") {
    imageSrc = "/characters/professor.png";
    characterName = "Prof. Sterling";
    characterRole = "Strict Oral Examiner";
    characterVibe = "Testing theoretical rigor, precision, and edge cases";
    themeRing = "border-navy/50 shadow-[0_0_40px_rgba(15,43,74,0.35)]";
    ambientGlow = "from-navy/20 via-transparent to-transparent";
  }

  // Animation CSS classes based on real conversation events
  let transformClasses = "transition-all duration-700 ease-out";
  let ringColor = themeRing;

  switch (animationState) {
    case "listening":
    case "recording":
      transformClasses += " scale-[1.03] translate-y-[-4px]";
      ringColor = "border-rose-500 shadow-[0_0_50px_rgba(225,29,72,0.4)]";
      break;

    case "speaking":
      transformClasses += " animate-pulse-gentle scale-[1.02]";
      ringColor = "border-emerald-500 shadow-[0_0_45px_rgba(16,185,129,0.35)]";
      break;

    case "thinking":
    case "transcribing":
      transformClasses += " -rotate-1 translate-y-[2px] opacity-95";
      ringColor = "border-amber-400 shadow-[0_0_35px_rgba(245,158,11,0.3)]";
      break;

    case "taking_notes":
      transformClasses += " translate-y-[4px] scale-[0.99]";
      ringColor = "border-cobalt/50 shadow-[0_0_30px_rgba(58,99,255,0.25)]";
      break;

    case "curious":
      transformClasses += " rotate-2 scale-[1.04] translate-y-[-6px]";
      ringColor = "border-gap-orange shadow-[0_0_35px_rgba(255,107,26,0.35)]";
      break;

    case "confused":
    case "skeptical":
      transformClasses += " -rotate-2 translate-x-[-3px]";
      ringColor = "border-amber-500/80 shadow-[0_0_35px_rgba(245,158,11,0.35)]";
      break;

    case "impressed":
      transformClasses += " scale-[1.05] translate-y-[-6px]";
      ringColor = "border-emerald-500 shadow-[0_0_45px_rgba(16,185,129,0.4)]";
      break;

    case "grumpy":
      transformClasses += " -rotate-1 translate-y-[6px]";
      ringColor = "border-rose-600 shadow-[0_0_45px_rgba(225,29,72,0.45)]";
      break;

    case "leaving":
      transformClasses += " translate-x-[80px] opacity-0 scale-90";
      break;

    case "teacher_transition":
      transformClasses += " animate-pulse scale-[1.06]";
      ringColor = "border-gap-orange shadow-[0_0_60px_rgba(255,107,26,0.5)]";
      break;

    case "idle":
    default:
      transformClasses += " animate-float";
      break;
  }

  // Derive human readable state badge
  let badgeLabel = "Waiting for you";
  let badgeColor = "bg-white/80 text-navy/70 border-fog";

  if (animationState === "recording" || animationState === "listening") {
    badgeLabel = "Listening to your answer...";
    badgeColor = "bg-rose-50 text-rose-700 border-rose-300 animate-pulse";
  } else if (animationState === "transcribing") {
    badgeLabel = "Processing speech...";
    badgeColor = "bg-amber-50 text-amber-700 border-amber-300";
  } else if (animationState === "thinking") {
    badgeLabel = "Thinking & Evaluating...";
    badgeColor = "bg-amber-50 text-amber-700 border-amber-300 animate-pulse";
  } else if (animationState === "taking_notes") {
    badgeLabel = "Taking notes...";
    badgeColor = "bg-cobalt/10 text-cobalt border-cobalt/30";
  } else if (animationState === "speaking") {
    badgeLabel = "Speaking response...";
    badgeColor = "bg-emerald-50 text-emerald-700 border-emerald-300";
  } else if (animationState === "impressed") {
    badgeLabel = "Impressed by explanation!";
    badgeColor = "bg-emerald-50 text-emerald-700 border-emerald-300";
  } else if (animationState === "curious") {
    badgeLabel = "Curious & asking follow-up";
    badgeColor = "bg-gap-orange/10 text-gap-orange border-gap-orange/30";
  } else if (animationState === "confused") {
    badgeLabel = "Puzzled by misconception";
    badgeColor = "bg-rose-50 text-rose-700 border-rose-300";
  } else if (animationState === "skeptical") {
    badgeLabel = "Testing edge cases";
    badgeColor = "bg-navy/10 text-navy border-navy/30";
  } else if (animationState === "grumpy") {
    badgeLabel = "Threshold reached";
    badgeColor = "bg-rose-50 text-rose-800 border-rose-400";
  } else if (animationState === "leaving") {
    badgeLabel = "Concluded interview";
    badgeColor = "bg-navy text-white border-navy";
  }

  return (
    <div className="w-full flex flex-col items-center justify-center relative select-none py-2">
      {/* Dynamic Ambient Background Glow */}
      <div
        className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-80 sm:w-96 sm:h-96 md:w-[460px] md:h-[460px] rounded-full bg-radial ${ambientGlow} pointer-events-none -z-10 blur-3xl transition-all duration-700`}
      />

      {/* Teacher Intervention Notice */}
      {isTeacherIntervention && (
        <div className="mb-4 inline-flex items-center gap-2 px-4 py-1.5 bg-gap-orange text-white rounded-full font-mono text-xs font-bold uppercase tracking-wider shadow-[0_3px_0_0_#C2410C] animate-bounce">
          <BookOpen className="w-4 h-4" />
          <span>TEACHER INTERVENTION ACTIVE</span>
        </div>
      )}

      {/* Central Character Stage Container */}
      <div className="relative group">
        {/* Floating Animated Status Badges */}
        <div className="absolute -top-3 -right-3 z-30">
          {animationState === "speaking" && (
            <div className="p-2.5 bg-emerald-500 text-white rounded-full shadow-lg animate-bounce">
              <Volume2 className="w-5 h-5" />
            </div>
          )}
          {(animationState === "listening" || animationState === "recording") && (
            <div className="p-2.5 bg-rose-600 text-white rounded-full shadow-lg animate-pulse">
              <Mic className="w-5 h-5" />
            </div>
          )}
          {(animationState === "thinking" || animationState === "transcribing") && (
            <div className="p-2.5 bg-amber-500 text-white rounded-full shadow-lg animate-spin">
              <Brain className="w-5 h-5" />
            </div>
          )}
          {animationState === "taking_notes" && (
            <div className="p-2.5 bg-cobalt text-white rounded-full shadow-lg">
              <FileEdit className="w-5 h-5" />
            </div>
          )}
          {animationState === "curious" && (
            <div className="p-2.5 bg-gap-orange text-white rounded-full shadow-lg animate-bounce">
              <HelpCircle className="w-5 h-5" />
            </div>
          )}
          {animationState === "impressed" && (
            <div className="p-2.5 bg-emerald-500 text-white rounded-full shadow-lg">
              <Sparkles className="w-5 h-5 text-amber-200" />
            </div>
          )}
          {(animationState === "confused" || animationState === "skeptical" || animationState === "grumpy") && (
            <div className="p-2.5 bg-rose-500 text-white rounded-full shadow-lg">
              <AlertCircle className="w-5 h-5" />
            </div>
          )}
        </div>

        {/* Animated Ripple Rings while User Speaks */}
        {(animationState === "listening" || animationState === "recording") && (
          <>
            <div className="absolute -inset-4 rounded-[24px] border-2 border-rose-500/40 animate-ping pointer-events-none" />
            <div className="absolute -inset-8 rounded-[30px] border border-rose-400/20 animate-pulse pointer-events-none" />
          </>
        )}

        {/* Outer Frame with physical keycap shadow */}
        <div
          className={`relative rounded-[20px] bg-white border-3 ${ringColor} p-2.5 shadow-[6px_8px_0_0_#0F2B4A] transition-all duration-500 overflow-hidden`}
        >
          {/* High-Res Master Character Container */}
          <div
            className={`w-64 h-80 sm:w-72 sm:h-92 md:w-80 md:h-[400px] flex items-center justify-center overflow-hidden rounded-[16px] bg-gradient-to-b from-[#F0F4F8] to-white relative ${transformClasses}`}
          >
            <img
              src={imageSrc}
              alt={characterName}
              className="w-full h-full object-contain select-none pointer-events-none drop-shadow-md transition-all duration-500"
            />

            {/* Speaking Audio Equalizer Bars at bottom */}
            {animationState === "speaking" && (
              <div className="absolute bottom-5 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-navy/85 backdrop-blur-md px-4 py-1.5 rounded-full shadow-md z-20">
                <span className="w-1 h-3 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.4s]" />
                <span className="w-1.5 h-6 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
                <span className="w-1 h-4 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.5s]" />
                <span className="w-1.5 h-8 bg-emerald-400 rounded-full animate-bounce" />
                <span className="w-1 h-5 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-7 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.1s]" />
                <span className="w-1 h-3 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.45s]" />
                <span className="font-mono text-[11px] font-bold text-white ml-2">
                  Speaking
                </span>
              </div>
            )}

            {/* Taking Notes Floating Animation */}
            {animationState === "taking_notes" && (
              <div className="absolute bottom-5 left-1/2 -translate-x-1/2 bg-amber-50 border-2 border-amber-300 shadow-md text-amber-900 px-3 py-1.5 rounded-[6px] font-mono text-xs font-bold flex items-center gap-2 animate-pulse z-20">
                <FileEdit className="w-4 h-4 text-amber-700" />
                Jotting Notes...
              </div>
            )}

            {/* Thinking Orbital Glow */}
            {(animationState === "thinking" || animationState === "transcribing") && (
              <div className="absolute bottom-5 left-1/2 -translate-x-1/2 bg-white/90 border-2 border-amber-400 shadow-md text-amber-900 px-3 py-1.5 rounded-[6px] font-mono text-xs font-bold flex items-center gap-2 z-20">
                <Brain className="w-4 h-4 text-amber-600 animate-spin" />
                Processing Explanation...
              </div>
            )}
          </div>
        </div>

        {/* Character Title Card */}
        <div className="mt-4 text-center flex flex-col items-center gap-1.5">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 bg-white border border-fog rounded-full shadow-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                character === "teacher"
                  ? "bg-gap-orange animate-pulse"
                  : character === "professor"
                  ? "bg-navy"
                  : "bg-cobalt"
              }`}
            />
            <span className="font-heading text-sm font-bold text-navy">
              {characterName}
            </span>
            <span className="font-mono text-xs text-navy/40">·</span>
            <span className="font-mono text-xs uppercase font-semibold text-navy/60">
              {characterRole}
            </span>
          </div>

          {/* Real-Time Interaction State Badge */}
          <div className="inline-flex items-center gap-1.5">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full border text-xs font-mono font-bold transition-all ${badgeColor}`}
            >
              {badgeLabel}
            </span>

            {/* Stop / Replay Speech Audio Buttons */}
            {isPlayingSpeech ? (
              <button
                onClick={onStopSpeech}
                className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-300 text-[11px] font-mono font-bold hover:bg-rose-100 transition-colors cursor-pointer"
                title="Stop audio speech"
              >
                MUTE
              </button>
            ) : (
              onReplaySpeech && (
                <button
                  onClick={onReplaySpeech}
                  className="px-2 py-0.5 rounded-full bg-white text-cobalt border border-fog text-[11px] font-mono font-bold hover:bg-ice transition-colors cursor-pointer inline-flex items-center gap-1"
                  title="Replay last spoken response"
                >
                  <Volume2 className="w-3 h-3 text-cobalt" />
                  REPLAY
                </button>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
