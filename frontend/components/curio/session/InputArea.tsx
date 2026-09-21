"use client";

import React, { useState, useRef, useEffect } from "react";
import { Plus, Mic, Send } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { SessionMode } from "@/types/session";
import { curioToast } from "@/components/curio/CurioToast";

export interface InputAreaProps {
  mode: SessionMode;
  onSendMessage: (content: string) => void;
  onStuck: () => void;
  onFinishSession: () => void;
  disabled?: boolean;
}

export function InputArea({
  mode,
  onSendMessage,
  onStuck,
  onFinishSession,
  disabled = false,
}: InputAreaProps) {
  const [content, setContent] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isTeacher = mode === "TEACHER";
  const placeholder = isTeacher
    ? "Ask Curio a question or explain your understanding..."
    : "Explain your reasoning to Curio...";

  const handleSend = () => {
    if (!content.trim() || disabled) return;
    onSendMessage(content.trim());
    setContent("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  const handleAttachmentClick = () => {
    curioToast.info("DOCUMENT INGESTION READY", "Document upload will be available in the next release.");
  };

  const handleVoiceClick = () => {
    curioToast.info("VOICE INGESTION READY", "Voice explanation input will be available in the next release.");
  };

  useEffect(() => {
    textareaRef.current?.focus();
  }, [mode]);

  return (
    <div className="w-full max-w-4xl mx-auto px-4 md:px-8 pb-6 pt-2">
      {/* Composer Box */}
      <div className="bg-white border-2 border-navy rounded-[8px] shadow-[0_4px_0_0_#0F2B4A] p-3 transition-all duration-150 focus-within:border-cobalt focus-within:shadow-[0_4px_0_0_#3A63FF]">
        <div className="flex items-end gap-2.5">
          {/* Attachment placeholder button */}
          <button
            type="button"
            onClick={handleAttachmentClick}
            className="p-2 text-navy/40 hover:text-navy hover:bg-ice rounded-[4px] transition-colors shrink-0 mb-0.5"
            title="Attach document or code file (Coming soon)"
          >
            <Plus className="w-4 h-4" />
          </button>

          {/* Main Textarea */}
          <textarea
            ref={textareaRef}
            rows={2}
            value={content}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="flex-1 resize-none bg-transparent font-sans text-sm md:text-base text-navy placeholder:text-navy/40 focus:outline-none min-h-[48px] max-h-[180px] py-1 leading-relaxed"
          />

          {/* Voice placeholder button */}
          <button
            type="button"
            onClick={handleVoiceClick}
            className="p-2 text-navy/40 hover:text-navy hover:bg-ice rounded-[4px] transition-colors shrink-0 mb-0.5"
            title="Voice explanation (Coming soon)"
          >
            <Mic className="w-4 h-4" />
          </button>

          {/* Send Button */}
          <KeycapButton
            onClick={handleSend}
            disabled={!content.trim() || disabled}
            variant="navy"
            size="md"
            className="shrink-0"
          >
            <span className="hidden sm:inline">{isTeacher ? "SUBMIT" : "EXPLAIN"}</span>
            <Send className="w-3.5 h-3.5 sm:ml-1" />
          </KeycapButton>
        </div>

        {/* Composer Footer Hints */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-fog/50 px-1 text-[11px] font-mono text-navy/50">
          <span>
            Press <kbd className="font-semibold text-navy bg-ice px-1 py-0.5 rounded-[2px]">Enter ↵</kbd> to send, <kbd className="font-semibold text-navy bg-ice px-1 py-0.5 rounded-[2px]">Shift+Enter</kbd> for newline
          </span>
          <span className="hidden sm:inline">
            {content.length > 0 ? `${content.length} chars` : ""}
          </span>
        </div>
      </div>

      {/* Sub-actions */}
      <div className="flex items-center justify-between mt-3 px-1">
        <KeycapButton
          onClick={onFinishSession}
          variant="ghost"
          size="sm"
          className="text-navy/80 hover:text-white text-xs"
        >
          [FINISH SESSION]
        </KeycapButton>

        <KeycapButton
          onClick={onStuck}
          disabled={isTeacher || disabled}
          variant={isTeacher ? "ghost" : "gap"}
          size="sm"
          title={isTeacher ? "Currently addressing identified gap" : "Ask Curio to teach this specific concept"}
          className="text-xs"
        >
          {isTeacher ? "[ADDRESSING GAP]" : "[I'M STUCK]"}
        </KeycapButton>
      </div>
    </div>
  );
}
