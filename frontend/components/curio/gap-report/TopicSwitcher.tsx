"use client";

import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { TopicOption } from "@/types/gapReport";

export interface TopicSwitcherProps {
  topics: TopicOption[];
  currentTopicId: string;
  onSelectTopic: (topicId: string) => void;
}

export function TopicSwitcher({
  topics,
  currentTopicId,
  onSelectTopic,
}: TopicSwitcherProps) {
  const currentIndex = topics.findIndex((t) => t.id === currentTopicId);

  const handlePrev = () => {
    if (topics.length <= 1) return;
    const prevIndex = (currentIndex - 1 + topics.length) % topics.length;
    onSelectTopic(topics[prevIndex].id);
  };

  const handleNext = () => {
    if (topics.length <= 1) return;
    const nextIndex = (currentIndex + 1) % topics.length;
    onSelectTopic(topics[nextIndex].id);
  };

  return (
    <div className="flex items-center gap-2 mb-4 overflow-x-auto py-1 select-none">
      <button
        onClick={handlePrev}
        className="p-1.5 rounded-[4px] border border-fog bg-white text-navy hover:bg-ice transition-colors"
        aria-label="Previous topic"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      <div className="flex items-center gap-2">
        {topics.map((t) => {
          const isActive = t.id === currentTopicId;
          return (
            <button
              key={t.id}
              onClick={() => onSelectTopic(t.id)}
              className={`px-3 py-1.5 rounded-[4px] font-mono text-xs font-semibold uppercase tracking-wider transition-all duration-150 whitespace-nowrap ${
                isActive
                  ? "bg-navy text-white shadow-sm border border-navy"
                  : "bg-ice text-navy/60 hover:text-navy hover:bg-fog/50 border border-fog"
              }`}
            >
              {t.name}
            </button>
          );
        })}
      </div>

      <button
        onClick={handleNext}
        className="p-1.5 rounded-[4px] border border-fog bg-white text-navy hover:bg-ice transition-colors"
        aria-label="Next topic"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}
