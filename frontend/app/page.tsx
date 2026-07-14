"use client";

import { useEffect, useState } from "react";
import { useSessionStore } from "@/stores/session-store";
import { Sidebar } from "@/components/sessions/sidebar";
import { ChatContainer } from "@/components/chat/chat-container";
import { TopicSelector } from "@/components/topic/topic-selector";

export default function Home() {
  const { activeSession, fetchSessions } = useSessionStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    fetchSessions();
    setMounted(true);
  }, [fetchSessions]);

  if (!mounted) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 border-l border-border/50">
        {!activeSession ? (
          <TopicSelector />
        ) : (
          <ChatContainer />
        )}
      </main>
    </div>
  );
}
