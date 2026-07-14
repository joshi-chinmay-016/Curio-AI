import { Message } from "@/types";
import { User, Sparkles } from "lucide-react";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.sender === "USER";

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex gap-4 max-w-[80%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        
        {/* Avatar */}
        <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? "bg-primary/20 text-primary" : "bg-blue-500/20 text-blue-400"
        }`}>
          {isUser ? <User size={20} /> : <Sparkles size={20} />}
        </div>

        {/* Bubble */}
        <div className={`px-5 py-3.5 rounded-2xl ${
          isUser
            ? "bg-primary/10 border border-primary/20 text-foreground rounded-tr-sm"
            : "bg-card border border-border/50 text-foreground rounded-tl-sm shadow-sm"
        }`}>
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

      </div>
    </div>
  );
}
