"use client";

import React, { useEffect, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";
import { ChatMessage } from "@/types/session";
import { ChatBubble } from "./ChatBubble";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { TeacherModeSeparator } from "./TeacherModeSeparator";
import { GapCard } from "./GapCard";

export interface ChatThreadProps {
  messages: ChatMessage[];
  isThinking: boolean;
  activeGap?: {
    title: string;
    conceptId: string;
    severity: "LOW" | "MEDIUM" | "HIGH";
  };
}

export function ChatThread({ messages, isThinking, activeGap }: ChatThreadProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Auto-scroll on new messages or thinking change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Monitor scroll position to show/hide "Scroll to bottom" button
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 120;
    setShowScrollBottom(!isNearBottom);
  };

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="relative flex-1 w-full h-full overflow-hidden flex flex-col">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 w-full max-w-4xl mx-auto px-4 md:px-8 py-6 overflow-y-auto flex flex-col justify-start"
      >
        {messages.map((msg) => {
          if (msg.type === "separator") {
            const isActivated = msg.content.includes("ACTIVATED");
            return (
              <React.Fragment key={msg.id}>
                <TeacherModeSeparator type={isActivated ? "activated" : "returning"} />
                {isActivated && activeGap && (
                  <GapCard title={activeGap.title} />
                )}
              </React.Fragment>
            );
          }

          return <ChatBubble key={msg.id} message={msg} />;
        })}

        {isThinking && <ThinkingIndicator />}

        <div ref={bottomRef} className="h-6 shrink-0" />
      </div>

      {/* Floating Scroll to Latest Button */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 right-8 z-30 p-2 rounded-full bg-white border-2 border-navy text-navy shadow-[2px_2px_0_0_#0F2B4A] hover:bg-navy hover:text-white transition-all duration-150 flex items-center gap-1.5 text-xs font-mono font-semibold"
          aria-label="Scroll to latest messages"
        >
          <ArrowDown className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">LATEST</span>
        </button>
      )}
    </div>
  );
}
