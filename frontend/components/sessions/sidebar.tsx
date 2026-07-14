import { useSessionStore } from "@/stores/session-store";
import { Plus, MessageSquare, Loader2 } from "lucide-react";

export function Sidebar() {
  const { sessions, activeSession, selectSession, clearActiveSession, isLoading } = useSessionStore();

  return (
    <div className="w-72 bg-card/50 backdrop-blur-sm border-r border-border/50 flex flex-col">
      <div className="p-4 border-b border-border/50">
        <button
          onClick={clearActiveSession}
          className="w-full flex items-center justify-center gap-2 bg-primary/10 hover:bg-primary/20 text-primary-foreground border border-primary/20 rounded-lg px-4 py-2.5 transition-all font-medium"
        >
          <Plus size={18} />
          <span>New Session</span>
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sessions.map((session) => (
          <button
            key={session.session_id}
            onClick={() => selectSession(session.session_id)}
            className={`w-full text-left px-3 py-3 rounded-lg flex items-start gap-3 transition-colors ${
              activeSession?.id === session.session_id
                ? "bg-primary/15 border border-primary/30"
                : "hover:bg-accent border border-transparent"
            }`}
          >
            <MessageSquare size={18} className="mt-0.5 text-blue-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {session.topic}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground bg-accent px-1.5 py-0.5 rounded">
                  {session.current_mode}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Lvl {session.difficulty}
                </span>
              </div>
            </div>
          </button>
        ))}
        {sessions.length === 0 && !isLoading && (
          <div className="text-center p-4 text-sm text-muted-foreground opacity-60">
            No active sessions.
          </div>
        )}
        {isLoading && (
          <div className="flex justify-center p-4">
            <Loader2 className="animate-spin text-muted-foreground w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  );
}
