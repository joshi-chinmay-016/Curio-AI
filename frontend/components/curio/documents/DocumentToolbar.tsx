"use client";

import React from "react";
import { Search, LayoutGrid, List, ArrowDownUp } from "lucide-react";
import { DocumentFilterStatus, DocumentSortOption } from "@/types/document";

export interface DocumentToolbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: DocumentFilterStatus;
  onStatusFilterChange: (status: DocumentFilterStatus) => void;
  sortBy: DocumentSortOption;
  onSortChange: (sort: DocumentSortOption) => void;
  viewMode: "grid" | "list";
  onViewModeChange: (mode: "grid" | "list") => void;
  totalCount: number;
  filteredCount: number;
}

export function DocumentToolbar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  sortBy,
  onSortChange,
  viewMode,
  onViewModeChange,
  totalCount,
  filteredCount,
}: DocumentToolbarProps) {
  const filterTabs: Array<{ id: DocumentFilterStatus; label: string }> = [
    { id: "ALL", label: "ALL" },
    { id: "READY", label: "READY" },
    { id: "PROCESSING", label: "PROCESSING" },
    { id: "FAILED", label: "FAILED" },
  ];

  return (
    <div className="bg-white dark:bg-[#0B1524] border-2 border-navy dark:border-[#2F4D73] rounded-[6px] shadow-editorial dark:shadow-[4px_4px_0_0_#040910] p-3.5 md:p-4 mb-6 space-y-3.5">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-navy/40 dark:text-[#829AB1] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search documents by filename..."
            className="w-full bg-ice/40 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] focus:border-cobalt focus:bg-white dark:focus:bg-[#16273F] rounded-[4px] pl-9.5 pr-3.5 py-1.5 text-xs font-mono text-navy dark:text-[#F0F4F8] placeholder:text-navy/40 dark:placeholder:text-[#627D98] outline-none transition-colors"
          />
        </div>

        {/* View mode & Sort controls */}
        <div className="flex items-center justify-between sm:justify-end gap-2.5">
          {/* Sort By Dropdown */}
          <div className="flex items-center gap-1.5 bg-ice/50 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] px-2.5 py-1.5 rounded-[4px] text-xs font-mono">
            <ArrowDownUp className="w-3.5 h-3.5 text-navy/50 dark:text-[#829AB1] shrink-0" />
            <select
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value as DocumentSortOption)}
              className="bg-transparent text-navy dark:text-[#F0F4F8] font-semibold outline-none cursor-pointer text-xs"
              aria-label="Sort documents"
            >
              <option value="NEWEST" className="dark:bg-[#0B1524] dark:text-[#F0F4F8]">Newest First</option>
              <option value="OLDEST" className="dark:bg-[#0B1524] dark:text-[#F0F4F8]">Oldest First</option>
              <option value="NAME" className="dark:bg-[#0B1524] dark:text-[#F0F4F8]">Name (A-Z)</option>
              <option value="SIZE" className="dark:bg-[#0B1524] dark:text-[#F0F4F8]">File Size</option>
            </select>
          </div>

          {/* Grid / List view toggle */}
          <div className="flex items-center border border-fog dark:border-[#1E3652] rounded-[4px] bg-ice/40 dark:bg-[#101F33] p-0.5">
            <button
              onClick={() => onViewModeChange("grid")}
              className={`p-1 rounded-[3px] transition-colors cursor-pointer ${
                viewMode === "grid"
                  ? "bg-white dark:bg-[#1A3254] text-navy dark:text-white shadow-xs border border-fog/60 dark:border-[#2F4D73] font-bold"
                  : "text-navy/40 dark:text-[#829AB1] hover:text-navy dark:hover:text-white"
              }`}
              aria-label="Grid layout"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onViewModeChange("list")}
              className={`p-1 rounded-[3px] transition-colors cursor-pointer ${
                viewMode === "list"
                  ? "bg-white dark:bg-[#1A3254] text-navy dark:text-white shadow-xs border border-fog/60 dark:border-[#2F4D73] font-bold"
                  : "text-navy/40 dark:text-[#829AB1] hover:text-navy dark:hover:text-white"
              }`}
              aria-label="List layout"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Counts */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2.5 border-t border-fog/50 dark:border-[#1E3652]">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {filterTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onStatusFilterChange(tab.id)}
              className={`px-2.5 py-1 rounded-[3px] text-[11px] font-mono font-bold uppercase tracking-wider transition-colors cursor-pointer ${
                statusFilter === tab.id
                  ? "bg-navy dark:bg-cobalt text-white"
                  : "bg-ice/50 dark:bg-[#101F33] text-navy/60 dark:text-[#BAC7D5] hover:text-navy dark:hover:text-white hover:bg-ice dark:hover:bg-[#1A3254]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="text-[11px] font-mono text-navy/50 dark:text-[#829AB1]">
          Showing <span className="font-bold text-navy dark:text-[#F0F4F8]">{filteredCount}</span> of{" "}
          <span className="font-bold text-navy dark:text-[#F0F4F8]">{totalCount}</span> documents
        </div>
      </div>
    </div>
  );
}
