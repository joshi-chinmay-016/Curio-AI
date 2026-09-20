"use client";

import { GapReport } from "@/types/gapReport";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface KnowledgeMapFallbackProps {
  report: GapReport;
  selectedConceptId: string | null;
  onSelectConcept: (conceptId: string) => void;
}

export default function KnowledgeMapFallback({
  report,
  selectedConceptId,
  onSelectConcept,
}: KnowledgeMapFallbackProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "STRONG":
        return <Badge className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Strong</Badge>;
      case "DEVELOPING":
        return <Badge className="bg-amber-500/20 text-amber-400 border border-amber-500/30">Developing</Badge>;
      case "GAP":
        return <Badge className="bg-red-500/20 text-red-400 border border-red-500/30">Gap</Badge>;
      case "RESOLVED":
        return <Badge className="bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">Resolved</Badge>;
      case "MISCONCEPTION":
        return <Badge className="bg-fuchsia-500/20 text-fuchsia-400 border border-fuchsia-500/30">Misconception</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-3 p-4 h-full overflow-y-auto">
      <div className="mb-4">
        <h3 className="font-semibold text-sm text-foreground">Knowledge Concept List</h3>
        <p className="text-xs text-muted-foreground">
          2D Accessible Fallback View
        </p>
      </div>

      <div className="space-y-2">
        {report.concepts.map((concept) => (
          <Card
            key={concept.id}
            className={`cursor-pointer transition-all ${
              selectedConceptId === concept.id
                ? "ring-2 ring-primary border-primary/50 bg-accent/40"
                : "hover:border-border/80 bg-card/60"
            }`}
            onClick={() => onSelectConcept(concept.id)}
          >
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0 pr-3">
                  <h4 className="font-medium text-sm text-foreground truncate">
                    {concept.name}
                  </h4>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Score: {concept.score}% • Confidence: {concept.confidence}%
                  </p>
                </div>
                {getStatusBadge(concept.status)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
