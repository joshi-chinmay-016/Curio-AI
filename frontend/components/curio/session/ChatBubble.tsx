"use client";

import React, { useState } from "react";
import { Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/types/session";
import { ModeChip } from "@/components/curio/ModeChip";
import { MarkdownContent } from "./MarkdownContent";

export interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isLearner = message.role === "learner";
  const isTeacher = message.mode === "TEACHER" && message.role === "curio";
  const isGap = Boolean(message.gapReference);

  if (message.type === "separator") {
    const isTeacherTransition = message.content.includes("PAUSE") || message.content.includes("TEACHER");
    return (
      <div className="w-full flex items-center justify-center my-6 gap-3">
        <div className="h-px flex-1 bg-fog/80" />
        <div
          className={cn(
            "font-mono text-[11px] font-bold tracking-wider px-3 py-1 rounded-[2px] border uppercase",
            isTeacherTransition
              ? "bg-[#FFF5EE] text-gap-orange border-gap-orange/30 shadow-sm"
              : "bg-cobalt/10 text-cobalt border-cobalt/20 shadow-sm"
          )}
        >
          {message.content.replace(/^[─\s]+|[─\s]+$/g, "")}
        </div>
        <div className="h-px flex-1 bg-fog/80" />
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
          <div className="bg-navy text-white rounded-[8px_2px_8px_8px] p-4 text-sm md:text-base font-sans leading-relaxed shadow-[2px_2px_0_0_rgba(15,43,74,0.15)] relative">
            <MarkdownContent content={message.content} className="text-white" />
          </div>

          <div className="flex items-center gap-2 mt-1 px-1">
            <button
              onClick={handleCopyText}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-navy/40 hover:text-navy p-0.5"
              title="Copy message"
            >
              {copied ? (
                <Check className="w-3 h-3 text-cobalt" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
            </button>
            <span className="font-mono text-[10px] text-navy/40 uppercase">
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
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-[2px] font-mono text-[10px] font-bold tracking-wider uppercase bg-cobalt/15 text-cobalt border border-cobalt/30">
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
            "p-5 text-sm md:text-base font-sans text-navy leading-relaxed transition-all duration-300 w-full",
            "rounded-[2px_8px_8px_8px] shadow-sm",
            isTeacher
              ? "bg-[#FFF8F5] border-l-[3px] border-l-gap-orange border-y border-r border-gap-orange/30"
              : message.isRestored
              ? "bg-white border-l-[3px] border-l-cobalt border-y border-r border-fog"
              : isGap
              ? "bg-white border-l-[3px] border-l-gap-orange border-y border-r border-fog"
              : "bg-white border border-fog"
          )}
        >
          <MarkdownContent content={message.content} />
        </div>

        {/* Footer info & copy on hover */}
        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="font-mono text-[10px] text-navy/40 uppercase">
            {message.timestamp} {message.turnNumber ? `· Turn ${message.turnNumber}` : ""}
          </span>
          <button
            onClick={handleCopyText}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-navy/40 hover:text-navy p-0.5"
            title="Copy message"
          >
            {copied ? (
              <Check className="w-3 h-3 text-cobalt" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
