"use client";

import { ArrowLeft, MoreHorizontal } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface GapReportHeaderProps {
  topicName: string;
  onBack: () => void;
}

export default function GapReportHeader({
  topicName,
  onBack,
}: GapReportHeaderProps) {
  return (
    <header className="border-b-2 border-navy bg-white px-6 py-3.5 flex items-center justify-between shrink-0 shadow-sm">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="flex items-center justify-center w-8 h-8 rounded-[4px] border-2 border-navy bg-white hover:bg-navy hover:text-white text-navy shadow-[2px_2px_0_0_#0F2B4A] transition-all active:translate-y-[2px] active:shadow-none"
          aria-label="Back"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-navy/60 bg-ice px-2 py-0.5 rounded-[3px] border border-navy/20">
            GAP REPORT
          </span>
          <span className="text-navy/30">/</span>
          <h2 className="font-sora text-xl md:text-2xl font-bold uppercase tracking-tight text-navy">
            {topicName}
          </h2>
        </div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="flex items-center justify-center w-8 h-8 rounded-[4px] border-2 border-navy bg-white hover:bg-navy hover:text-white text-navy shadow-[2px_2px_0_0_#0F2B4A] transition-all active:translate-y-[2px] active:shadow-none"
            aria-label="More Options"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="border-2 border-navy shadow-[4px_4px_0_0_#0F2B4A] rounded-none">
          <DropdownMenuItem disabled className="font-mono text-xs uppercase">
            Export Report (Coming Soon)
          </DropdownMenuItem>
          <DropdownMenuItem disabled className="font-mono text-xs uppercase">
            Share Report (Coming Soon)
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
