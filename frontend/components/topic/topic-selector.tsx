import { useState } from "react";
import { useSessionStore } from "@/stores/session-store";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";

export function TopicSelector() {
  const { createSession, isLoading } = useSessionStore();
  const [topic, setTopic] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    await createSession(topic.trim());
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="max-w-xl w-full bg-card/40 backdrop-blur-md border border-border/50 rounded-2xl p-8 shadow-2xl">
        <div className="flex justify-center mb-6">
          <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-blue-400" />
          </div>
        </div>
        
        <h1 className="text-3xl font-bold text-center text-foreground mb-3">
          What do you want to teach?
        </h1>
        <p className="text-center text-muted-foreground mb-8">
          Enter a topic you want to master. I'll ask you questions about it.
        </p>

        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Recursion, Ohm's Law, React Hooks..."
            className="w-full bg-background border border-border/50 rounded-xl px-5 py-4 text-lg text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-muted-foreground/50 pr-14"
            disabled={isLoading}
            autoFocus
          />
          <button
            type="submit"
            disabled={!topic.trim() || isLoading}
            className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all disabled:opacity-50 disabled:hover:bg-blue-500"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
          </button>
        </form>

        <div className="mt-6 flex flex-wrap gap-2 justify-center">
          {["Quantum Computing", "Event Loop", "Photosynthesis", "Neural Networks"].map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setTopic(suggestion)}
              className="px-3 py-1.5 rounded-full border border-border/50 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
