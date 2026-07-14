import { useEffect, useRef } from "react";
import { useSessionStore } from "@/stores/session-store";
import { MessageBubble } from "./message-bubble";
import { ChatInput } from "./chat-input";
import { EvaluationReport } from "../reports/evaluation-report";

export function ChatContainer() {
  const { activeSession, messages, activeReport, endActiveSession } = useSessionStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  if (activeSession?.status === "COMPLETED" && activeReport) {
    return <EvaluationReport report={activeReport} />;
  }

  return (
    <div className="flex-1 flex flex-col h-full relative">
      {/* Header */}
      <div className="h-14 border-b border-border/50 flex items-center justify-between px-6 bg-card/50 backdrop-blur-md sticky top-0 z-10">
        <div>
          <h2 className="font-semibold text-foreground">
            {activeSession?.topic}
          </h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${
              activeSession?.state?.current_mode === "TEACHER" ? "bg-amber-400" : "bg-blue-400"
            }`} />
            <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              {activeSession?.state?.current_mode} MODE
            </span>
          </div>
          <button
            onClick={() => endActiveSession()}
            className="text-sm px-3 py-1.5 bg-danger/10 hover:bg-danger/20 text-danger rounded-md transition-colors"
          >
            End Session
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((message) => (
          <MessageBubble key={message.message_id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-background/80 backdrop-blur-md border-t border-border/50">
        <ChatInput />
      </div>
    </div>
  );
}
