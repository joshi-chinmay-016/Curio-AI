"use client";

import React, { memo } from "react";
import {
  CharacterId,
  PerformanceState,
} from "@/types/performanceEngine";
import { CharacterTransition } from "./CharacterTransition";
import { Volume2, VolumeX, RotateCcw } from "lucide-react";

interface CharacterStageProps {
  character: CharacterId;
  performanceState: PerformanceState;
  prefersReducedMotion?: boolean;
  isPlayingSpeech?: boolean;
  statusLabel?: string;
  clipboardMark?: "none" | "check" | "cross" | "in-progress";
  onStopSpeech?: () => void;
  onReplaySpeech?: () => void;
}

export const CharacterStage = memo(function CharacterStage({
  character,
  performanceState,
  prefersReducedMotion = false,
  isPlayingSpeech = false,
  statusLabel,
  clipboardMark = "none",
  onStopSpeech,
  onReplaySpeech,
}: CharacterStageProps) {
  // Theme ambient styling
  let badgeColor = "bg-cobalt/15 text-cobalt border-cobalt/30";
  let ambientBg = "from-cobalt/10 via-transparent to-transparent";
  let ringBorder = "border-cobalt/30 shadow-[0_0_50px_rgba(58,99,255,0.18)]";
  let characterName = "Leo";
  let roleTitle = "Curious Student";

  if (character === "TEACHER") {
    badgeColor = "bg-gap-orange/15 text-gap-orange border-gap-orange/30";
    ambientBg = "from-gap-orange/10 via-transparent to-transparent";
    ringBorder = "border-gap-orange/30 shadow-[0_0_50px_rgba(255,107,26,0.18)]";
    characterName = "Ms. Clara";
    roleTitle = "Pedagogical Guide";
  } else if (character === "PROFESSOR") {
    badgeColor = "bg-slate-700/20 text-slate-200 border-slate-600/40";
    ambientBg = "from-slate-700/15 via-transparent to-transparent";
    ringBorder = "border-slate-600/30 shadow-[0_0_50px_rgba(30,41,59,0.25)]";
    characterName = "Prof. Sterling";
    roleTitle = "Oral Examiner";
  }

  // Derive human-readable status badge text
  let displayStatus = statusLabel;
  if (!displayStatus) {
    switch (performanceState) {
      case "ENTERING":
        displayStatus = "Entering stage...";
        break;
      case "LISTENING_ACTIVE":
      case "LISTENING_IDLE":
        displayStatus = "Listening attentively...";
        break;
      case "THINKING":
        displayStatus = "Reflecting...";
        break;
      case "EVALUATING":
        displayStatus = "Evaluating rigor...";
        break;
      case "TAKING_NOTES":
        displayStatus = "Taking notes...";
        break;
      case "MARKING":
        displayStatus = "Marking clipboard...";
        break;
      case "EXPLAINING":
        displayStatus = "Clarifying concept...";
        break;
      case "ASKING":
        displayStatus = "Inquiring...";
        break;
      case "SPEAKING":
        displayStatus = "Speaking...";
        break;
      case "REACTING_POSITIVE":
        displayStatus = "Impressed!";
        break;
      case "REACTING_CONFUSED":
        displayStatus = "Pondering gap...";
        break;
      case "REACTING_STRICT":
        displayStatus = "Questioning premise...";
        break;
      case "REACTING_GRUMPY":
        displayStatus = "Departing session...";
        break;
      case "EXITING":
        displayStatus = "Exiting...";
        break;
      default:
        displayStatus = "Ready";
    }
  }

  return (
    <div
      className="relative w-full max-w-[420px] mx-auto flex flex-col items-center select-none"
      data-testid="character-stage-container"
    >
      {/* 1. Stage Card Container */}
      <div
        className={`relative w-full h-[360px] md:h-[400px] rounded-3xl bg-gradient-to-b ${ambientBg} bg-navy-surface/90 border ${ringBorder} flex flex-col items-center justify-between p-4 overflow-hidden transition-all duration-700 backdrop-blur-md`}
      >
        {/* Subtle radial floor spotlight under character feet */}
        <div className="absolute bottom-6 w-[240px] h-[36px] rounded-full bg-black/25 blur-md pointer-events-none" />

        {/* Top Header Strip: Character Name + Live Status Pill */}
        <div className="w-full flex items-center justify-between z-10">
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-wide text-white flex items-center gap-1.5">
              {characterName}
              <span className="text-xs font-normal text-slate-400">({roleTitle})</span>
            </span>
          </div>

          <div
            className={`px-3 py-1 rounded-full border text-xs font-mono font-medium tracking-wide flex items-center gap-1.5 ${badgeColor}`}
          >
            {isPlayingSpeech && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
            )}
            {displayStatus}
          </div>
        </div>

        {/* Character Visual Center */}
        <div className="relative w-full flex-1 flex items-center justify-center">
          <CharacterTransition
            activeCharacter={character}
            performanceState={performanceState}
            prefersReducedMotion={prefersReducedMotion}
            clipboardMark={clipboardMark}
          />
        </div>

        {/* Bottom Audio Helper Bar (Stop / Replay) */}
        <div className="w-full flex items-center justify-between z-10 px-2 py-1 text-xs text-slate-400 border-t border-white/5">
          <div className="flex items-center gap-1.5">
            <Volume2 className="w-3.5 h-3.5 text-slate-500" />
            <span className="font-mono text-[11px]">Audio First</span>
          </div>

          <div className="flex items-center gap-2">
            {isPlayingSpeech && onStopSpeech && (
              <button
                type="button"
                onClick={onStopSpeech}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors flex items-center gap-1 text-[11px]"
                title="Stop Audio Playback"
              >
                <VolumeX className="w-3 h-3 text-rose-400" />
                Stop
              </button>
            )}
            {onReplaySpeech && !isPlayingSpeech && (
              <button
                type="button"
                onClick={onReplaySpeech}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors flex items-center gap-1 text-[11px]"
                title="Replay Audio"
              >
                <RotateCcw className="w-3 h-3 text-slate-400" />
                Replay
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});
