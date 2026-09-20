"use client";

import { Button } from "@/components/ui/button";
import { RotateCcw, Filter, Eye, AlertTriangle } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface KnowledgeMapControlsProps {
  filterMode: "all" | "gaps";
  onFilterChange: (mode: "all" | "gaps") => void;
  onResetView: () => void;
}

export default function KnowledgeMapControls({
  filterMode,
  onFilterChange,
  onResetView,
}: KnowledgeMapControlsProps) {
  return (
    <div className="absolute bottom-4 right-4 flex gap-2 z-10">
      <Button
        variant="outline"
        size="sm"
        onClick={onResetView}
        className="bg-card/90 backdrop-blur-md border-border/80 shadow-md text-xs hover:bg-accent"
      >
        <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
        Reset View
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="bg-card/90 backdrop-blur-md border-border/80 shadow-md text-xs hover:bg-accent"
          >
            <Filter className="h-3.5 w-3.5 mr-1.5" />
            {filterMode === "gaps" ? "Gaps Only" : "Show All"}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onClick={() => onFilterChange("all")}
            className={filterMode === "all" ? "bg-accent font-medium" : ""}
          >
            <Eye className="h-3.5 w-3.5 mr-2 text-blue-400" />
            Show All Concepts
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => onFilterChange("gaps")}
            className={filterMode === "gaps" ? "bg-accent font-medium" : ""}
          >
            <AlertTriangle className="h-3.5 w-3.5 mr-2 text-amber-400" />
            Focus on Gaps Only
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
