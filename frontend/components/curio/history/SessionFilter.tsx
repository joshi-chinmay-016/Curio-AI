"use client";

import React from "react";

export type HistoryFilterType = "ALL" | "IN_PROGRESS" | "COMPLETED" | "PRACTICE_QUEUE";

export interface SessionFilterProps {
  activeFilter: HistoryFilterType;
  onFilterChange: (filter: HistoryFilterType) => void;
  practiceQueueCount: number;
}

export function SessionFilter({
  activeFilter,
  onFilterChange,
  practiceQueueCount,
}: SessionFilterProps) {
  const tabs: { key: HistoryFilterType; label: string; count?: number }[] = [
    { key: "ALL", label: "ALL" },
    { key: "IN_PROGRESS", label: "IN PROGRESS" },
    { key: "COMPLETED", label: "COMPLETED" },
    { key: "PRACTICE_QUEUE", label: "PRACTICE QUEUE", count: practiceQueueCount },
  ];

  return (
    <div className="flex items-center gap-2 overflow-x-auto py-2 border-b border-fog/80 dark:border-[#1E3652] mb-6">
      {tabs.map((tab) => {
        const isActive = activeFilter === tab.key;
        return (
          <button
            key={tab.key}
            onClick={() => onFilterChange(tab.key)}
            className={`px-4 py-2 rounded-full font-mono text-xs font-semibold uppercase tracking-wider transition-all duration-150 whitespace-nowrap flex items-center gap-2 cursor-pointer ${
              isActive
                ? "bg-navy dark:bg-cobalt text-white shadow-sm"
                : "bg-white dark:bg-[#101F33] text-navy/70 dark:text-[#C5D0DE] hover:text-navy dark:hover:text-white hover:bg-ice dark:hover:bg-[#1A3254] border border-fog dark:border-[#1E3652]"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  isActive ? "bg-gap-orange text-white" : "bg-ice dark:bg-[#16273F] text-navy dark:text-[#F0F4F8]"
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
