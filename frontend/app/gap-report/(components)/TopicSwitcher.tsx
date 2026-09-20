"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { TopicOption } from "@/types/gapReport";

interface TopicSwitcherProps {
  topics: TopicOption[];
  activeTopicId: string;
  onTopicChange: (topicId: string) => void;
}

export default function TopicSwitcher({
  topics,
  activeTopicId,
  onTopicChange,
}: TopicSwitcherProps) {
  const currentIndex = topics.findIndex((t) => t.id === activeTopicId);

  const handlePrev = () => {
    if (currentIndex > 0) {
      onTopicChange(topics[currentIndex - 1].id);
    } else {
      onTopicChange(topics[topics.length - 1].id);
    }
  };

  const handleNext = () => {
    if (currentIndex < topics.length - 1) {
      onTopicChange(topics[currentIndex + 1].id);
    } else {
      onTopicChange(topics[0].id);
    }
  };

  return (
    <div className="flex items-center justify-between bg-white border border-navy/20 rounded-[6px] px-3 py-2 shadow-sm mb-4 shrink-0">
      <button
        onClick={handlePrev}
        className="p-1 text-navy hover:text-cobalt transition-colors focus:outline-none"
        aria-label="Previous Topic"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      <div className="flex items-center gap-2 overflow-x-auto py-0.5 px-2 no-scrollbar">
        {topics.map((topic) => {
          const isActive = topic.id === activeTopicId;
          return (
            <button
              key={topic.id}
              onClick={() => onTopicChange(topic.id)}
              className={`font-mono text-xs uppercase px-3 py-1.5 rounded-[4px] font-semibold transition-all duration-150 whitespace-nowrap select-none ${
                isActive
                  ? "bg-navy text-white shadow-sm"
                  : "bg-ice text-navy/60 hover:text-navy hover:bg-ice/80"
              }`}
            >
              {topic.name}
            </button>
          );
        })}
      </div>

      <button
        onClick={handleNext}
        className="p-1 text-navy hover:text-cobalt transition-colors focus:outline-none"
        aria-label="Next Topic"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
