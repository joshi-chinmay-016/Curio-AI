import { useState, useRef, useEffect } from "react";
import { useSessionStore } from "@/stores/session-store";
import { Send, Loader2 } from "lucide-react";

export function ChatInput() {
  const { sendMessage, isLoading } = useSessionStore();
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [text]);

  const handleSubmit = async () => {
    if (!text.trim() || isLoading) return;
    const content = text.trim();
    setText("");
    await sendMessage(content);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="max-w-4xl mx-auto relative flex items-end gap-2 bg-card border border-border/50 rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary/30 transition-all">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your explanation here..."
        className="flex-1 max-h-48 min-h-[44px] bg-transparent resize-none py-3 px-4 text-foreground placeholder:text-muted-foreground focus:outline-none"
        disabled={isLoading}
        rows={1}
      />
      <button
        onClick={handleSubmit}
        disabled={!text.trim() || isLoading}
        className="w-11 h-11 shrink-0 flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white rounded-xl transition-all disabled:opacity-50 disabled:hover:bg-blue-500 mb-0.5 mr-0.5"
      >
        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
      </button>
    </div>
  );
}
