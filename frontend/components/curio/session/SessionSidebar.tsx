"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Settings,
  BookOpen,
  X,
} from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { getSessionHistory } from "@/services/historyService";
import { SessionSummary } from "@/types/history";

export interface SessionSidebarProps {
  activeSessionId: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

function formatRelativeTime(dateString?: string): string {
  if (!dateString) return "";
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function SessionSidebar({
  activeSessionId,
  isCollapsed,
  onToggleCollapse,
  mobileOpen = false,
  onMobileClose,
}: SessionSidebarProps) {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  const refreshSessions = () => {
    getSessionHistory().then((data) => setSessions(data));
  };

  useEffect(() => {
    refreshSessions();
  }, [activeSessionId]);

  const filteredSessions = sessions.filter((s) =>
    s.topicName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={onMobileClose}
          className="fixed inset-0 z-40 bg-navy/40 backdrop-blur-[1px] md:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 flex flex-col bg-white border-r border-fog transition-all duration-300 ${
          isCollapsed ? "w-0 md:w-16 overflow-hidden" : "w-72 md:w-72"
        } ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        {/* Header */}
        <div className="p-4 border-b border-fog flex items-center justify-between shrink-0">
          {!isCollapsed ? (
            <div className="flex items-center justify-between w-full">
              <Link
                href="/"
                className="font-mono text-lg font-bold tracking-wider text-navy flex items-center gap-1.5"
              >
                <span>CURIO</span>
                <span className="text-gap-orange">.</span>
              </Link>
              <button
                onClick={onToggleCollapse}
                className="p-1.5 text-navy/60 hover:text-navy hover:bg-ice rounded-[4px] transition-colors hidden md:block"
                title="Collapse sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {onMobileClose && (
                <button
                  onClick={onMobileClose}
                  className="p-1.5 text-navy/60 hover:text-navy md:hidden"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <button
                onClick={onToggleCollapse}
                className="p-1.5 text-navy/60 hover:text-navy hover:bg-ice rounded-[4px] transition-colors"
                title="Expand sidebar"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Content Area */}
        {!isCollapsed && (
          <div className="flex-1 flex flex-col min-h-0 p-3">
            {/* New Session Button */}
            <Link href="/topics" className="w-full mb-3">
              <KeycapButton
                variant="navy"
                size="sm"
                className="w-full justify-center gap-1.5 text-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                NEW SESSION
              </KeycapButton>
            </Link>

            {/* Search Filter */}
            <div className="relative mb-3">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-navy/40" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search sessions..."
                className="w-full bg-ice/60 border border-fog/80 rounded-[4px] pl-8 pr-3 py-1.5 font-sans text-xs text-navy placeholder:text-navy/40 focus:outline-none focus:border-cobalt"
              />
            </div>

            {/* Session List */}
            <div className="flex-1 overflow-y-auto space-y-1 pr-1">
              <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/40 px-2 py-1">
                RECENT SESSIONS
              </div>

              {filteredSessions.length > 0 ? (
                filteredSessions.map((session) => {
                  const isActive = session.sessionId === activeSessionId;
                  return (
                    <Link
                      key={session.sessionId}
                      href={`/session/${session.sessionId}?topic=${encodeURIComponent(
                        session.topicName
                      )}`}
                      className={`flex items-start gap-2.5 px-3 py-2 rounded-[4px] text-xs transition-colors group ${
                        isActive
                          ? "bg-navy text-white font-medium shadow-sm"
                          : "text-navy/80 hover:bg-ice hover:text-navy"
                      }`}
                    >
                      <MessageSquare
                        className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${
                          isActive ? "text-cobalt" : "text-navy/40 group-hover:text-navy"
                        }`}
                      />
                      <div className="truncate flex-1">
                        <div className="flex items-center justify-between gap-1">
                          <span className="truncate">{session.topicName}</span>
                          <span className={`text-[9px] font-mono shrink-0 ${isActive ? "text-white/60" : "text-navy/40"}`}>
                            {formatRelativeTime(session.createdAt)}
                          </span>
                        </div>
                        <div
                          className={`text-[10px] font-mono mt-0.5 ${
                            isActive ? "text-white/60" : "text-navy/40"
                          }`}
                        >
                          {session.turnCount} turns · {session.understandingScore}%
                        </div>
                      </div>
                    </Link>
                  );
                })
              ) : (
                <div className="text-center py-6 text-xs text-navy/40 font-sans">
                  No sessions found
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="pt-3 border-t border-fog mt-auto space-y-1">
              <Link
                href="/history"
                className="flex items-center gap-2.5 px-3 py-2 rounded-[4px] text-xs text-navy/70 hover:text-navy hover:bg-ice transition-colors font-mono"
              >
                <BookOpen className="w-3.5 h-3.5 text-navy/50" />
                <span>ALL SESSIONS</span>
              </Link>
              <Link
                href="/settings"
                className="flex items-center gap-2.5 px-3 py-2 rounded-[4px] text-xs text-navy/70 hover:text-navy hover:bg-ice transition-colors font-mono"
              >
                <Settings className="w-3.5 h-3.5 text-navy/50" />
                <span>SETTINGS</span>
              </Link>
            </div>
          </div>
        )}

        {/* Collapsed icon bar on desktop */}
        {isCollapsed && (
          <div className="flex-1 flex flex-col items-center py-4 space-y-4">
            <Link
              href="/topics"
              className="p-2 text-navy/70 hover:text-navy hover:bg-ice rounded-[4px] transition-colors"
              title="New Session"
            >
              <Plus className="w-5 h-5" />
            </Link>
            <Link
              href="/history"
              className="p-2 text-navy/70 hover:text-navy hover:bg-ice rounded-[4px] transition-colors"
              title="All Sessions"
            >
              <BookOpen className="w-5 h-5" />
            </Link>
            <Link
              href="/settings"
              className="p-2 text-navy/70 hover:text-navy hover:bg-ice rounded-[4px] transition-colors mt-auto"
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </Link>
          </div>
        )}
      </aside>
    </>
  );
}
