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
    <div className="flex items-center gap-2 overflow-x-auto py-2 border-b border-fog/80 mb-6">
      {tabs.map((tab) => {
        const isActive = activeFilter === tab.key;
        return (
          <button
            key={tab.key}
            onClick={() => onFilterChange(tab.key)}
            className={`px-4 py-2 rounded-full font-mono text-xs font-semibold uppercase tracking-wider transition-all duration-150 whitespace-nowrap flex items-center gap-2 ${
              isActive
                ? "bg-navy text-white shadow-sm"
                : "bg-white text-navy/70 hover:text-navy hover:bg-ice border border-fog"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  isActive ? "bg-gap-orange text-white" : "bg-ice text-navy"
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
