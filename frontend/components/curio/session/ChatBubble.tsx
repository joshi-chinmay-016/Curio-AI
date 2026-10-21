"use client";

import React, { useState } from "react";
import { Copy, Check, BookOpen, Volume2, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/types/session";
import { ModeChip } from "@/components/curio/ModeChip";
import { MarkdownContent } from "./MarkdownContent";
import { useSpeechPlayback } from "@/hooks/useSpeechPlayback";

export interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isLearner = message.role === "learner";
  const isTeacher = message.mode === "TEACHER" && message.role === "curio";
  const isGap = Boolean(message.gapReference);

  const { isPlaying, isSupported, toggle: toggleSpeech } = useSpeechPlayback(
    message.id,
    message.content
  );

  if (message.type === "separator") {
    const isTeacherTransition = message.content.includes("PAUSE") || message.content.includes("TEACHER");
    return (
      <div className="w-full flex items-center justify-center my-6 gap-3">
        <div className="h-px flex-1 bg-fog/80 dark:bg-[#1E3652]" />
        <div
          className={cn(
            "font-mono text-[11px] font-bold tracking-wider px-3 py-1 rounded-[2px] border uppercase",
            isTeacherTransition
              ? "bg-[#FFF5EE] dark:bg-[#2A170F] text-gap-orange border-gap-orange/30 dark:border-gap-orange/50 shadow-sm"
              : "bg-cobalt/10 dark:bg-cobalt/20 text-cobalt dark:text-[#688BFF] border-cobalt/20 dark:border-cobalt/40 shadow-sm"
          )}
        >
          {message.content.replace(/^[─\s]+|[─\s]+$/g, "")}
        </div>
        <div className="h-px flex-1 bg-fog/80 dark:bg-[#1E3652]" />
      </div>
    );
  }

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard fallback
    }
  };

  if (isLearner) {
    return (
      <div className="group flex justify-end w-full my-4">
        <div className="flex flex-col items-end max-w-[88%] md:max-w-[72%]">
          <div className="bg-navy dark:bg-[#152E4D] dark:border dark:border-[#2F4D73] text-white rounded-[8px_2px_8px_8px] p-4 text-sm md:text-base font-sans leading-relaxed shadow-[2px_2px_0_0_rgba(15,43,74,0.15)] dark:shadow-[2px_2px_0_0_rgba(0,0,0,0.5)] relative">
            <MarkdownContent content={message.content} className="text-white" />
          </div>

          <div className="flex items-center gap-2 mt-1.5 px-1">
            <button
              onClick={handleCopyText}
              className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[4px] border text-xs font-mono transition-all duration-150 cursor-pointer ${
                copied
                  ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700 font-semibold"
                  : "bg-white dark:bg-[#101F33] text-navy/70 dark:text-[#C5D0DE] border-fog/90 dark:border-[#1E3652] hover:text-navy dark:hover:text-white hover:bg-ice dark:hover:bg-[#1A3254] hover:border-navy/30 dark:hover:border-[#2F4D73] shadow-xs"
              }`}
              title="Copy message text"
              aria-label="Copy message text"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                  <span className="text-[10px]">COPIED</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 text-navy/60 dark:text-[#829AB1]" />
                  <span className="text-[10px] font-medium">COPY</span>
                </>
              )}
            </button>
            <span className="font-mono text-[10px] text-navy/50 dark:text-[#829AB1] uppercase tracking-wider">
              {message.timestamp}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Curio Bubble
  return (
    <div className="group flex justify-start w-full my-4">
      <div className="flex flex-col items-start max-w-[88%] md:max-w-[75%]">
        {/* Chip Header */}
        <div className="flex items-center gap-2 mb-1.5">
          <ModeChip mode={isTeacher ? "TEACHER" : "STUDENT"} />
          {message.isRestored && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-[2px] font-mono text-[10px] font-bold tracking-wider uppercase bg-cobalt/15 text-cobalt dark:text-[#688BFF] border border-cobalt/30 dark:border-cobalt/50">
              RESTORED QUESTION
            </span>
          )}
          {message.isVerified && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-[2px] font-mono text-[10px] font-bold tracking-wider uppercase bg-cobalt text-white">
              ✓ VERIFIED
            </span>
          )}
        </div>

        {/* Bubble Box */}
        <div
          className={cn(
            "p-5 text-sm md:text-base font-sans text-navy dark:text-[#F0F4F8] leading-relaxed transition-all duration-300 w-full",
            "rounded-[2px_8px_8px_8px] shadow-sm",
            isTeacher
              ? "bg-[#FFF8F5] dark:bg-[#211510] border-l-[3px] border-l-gap-orange border-y border-r border-gap-orange/30 dark:border-gap-orange/50"
              : message.isRestored
              ? "bg-white dark:bg-[#0E1A2B] border-l-[3px] border-l-cobalt border-y border-r border-fog dark:border-[#1E3652]"
              : isGap
              ? "bg-white dark:bg-[#0E1A2B] border-l-[3px] border-l-gap-orange border-y border-r border-fog dark:border-[#1E3652]"
              : "bg-white dark:bg-[#0E1A2B] border border-fog dark:border-[#1E3652]"
          )}
        >
          <MarkdownContent content={message.content} />
        </div>

        {/* Source Citations (Rendered only when real citation metadata is returned) */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 w-full space-y-1.5 pl-1">
            <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-500 dark:text-[#829AB1] font-semibold">
              <BookOpen className="w-3 h-3 text-cobalt" />
              <span>Grounding Sources ({message.citations.length})</span>
            </div>
            <div className="space-y-1">
              {message.citations.map((cite, idx) => (
                <div
                  key={idx}
                  className="p-2 rounded bg-white/80 dark:bg-[#101F33] border border-slate-200 dark:border-[#1E3652] text-xs font-sans text-navy dark:text-[#F0F4F8]"
                >
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-600 dark:text-[#BAC7D5] font-medium mb-0.5">
                    <span className="truncate">{cite.documentName || "Document Source"}</span>
                    {cite.pageNumber !== null && cite.pageNumber !== undefined && (
                      <span className="shrink-0 text-slate-400 dark:text-[#829AB1]">p. {cite.pageNumber}</span>
                    )}
                  </div>
                  {cite.snippet && (
                    <p className="text-[11px] text-slate-500 dark:text-[#829AB1] italic line-clamp-2">
                      &ldquo;{cite.snippet}&rdquo;
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer info & copy / speak controls */}
        <div className="flex items-center gap-2 mt-2 px-1 flex-wrap">
          <span className="font-mono text-[10px] text-navy/50 dark:text-[#829AB1] uppercase tracking-wider mr-1">
            {message.timestamp} {message.turnNumber ? `· Turn ${message.turnNumber}` : ""}
          </span>

          {/* Copy Button - Clearly visible pill */}
          <button
            onClick={handleCopyText}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[4px] border text-xs font-mono transition-all duration-150 cursor-pointer ${
              copied
                ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700 font-semibold"
                : "bg-white dark:bg-[#101F33] text-navy/70 dark:text-[#C5D0DE] border-fog/90 dark:border-[#1E3652] hover:text-navy dark:hover:text-white hover:bg-ice dark:hover:bg-[#1A3254] hover:border-navy/30 dark:hover:border-[#2F4D73] shadow-xs"
            }`}
            title="Copy response text"
            aria-label="Copy message text"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-[11px]">COPIED</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-navy/60 dark:text-[#829AB1] group-hover:text-navy dark:group-hover:text-white" />
                <span className="text-[11px] font-medium">COPY</span>
              </>
            )}
          </button>

          {/* Read Aloud Button - Clearly visible pill */}
          {isSupported && (
            <button
              onClick={toggleSpeech}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[4px] border text-xs font-mono transition-all duration-150 cursor-pointer ${
                isPlaying
                  ? "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-700 font-semibold shadow-xs"
                  : "bg-white dark:bg-[#101F33] text-navy/70 dark:text-[#C5D0DE] border-fog/90 dark:border-[#1E3652] hover:text-cobalt dark:hover:text-[#4D7CFF] hover:bg-cobalt/5 dark:hover:bg-cobalt/20 hover:border-cobalt/40 dark:hover:border-cobalt/60 shadow-xs"
              }`}
              title={isPlaying ? "Stop reading aloud" : "Read aloud response"}
              aria-label={isPlaying ? "Stop reading aloud" : "Read aloud response"}
            >
              {isPlaying ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current text-rose-600 dark:text-rose-400 animate-pulse" />
                  <span className="text-[11px] text-rose-700 dark:text-rose-300 font-semibold">STOP</span>
                </>
              ) : (
                <>
                  <Volume2 className="w-3.5 h-3.5 text-cobalt" />
                  <span className="text-[11px] font-medium">READ ALOUD</span>
                </>
              )}
            </button>
          )}

          {isPlaying && (
            <span className="inline-flex items-center gap-1.5 font-mono text-[11px] text-rose-600 dark:text-rose-400 font-semibold bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 px-2 py-0.5 rounded-[4px] animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-600 dark:bg-rose-400 animate-ping" />
              Speaking...
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
