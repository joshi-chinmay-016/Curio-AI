"use client";

import { useState } from "react";
import { KeycapButton } from "@/components/ui/KeycapButton";
import { useToast } from "@/hooks/use-toast";
import {
  practiceGap,
  saveGapForLater,
  markConceptForReview,
} from "@/services/gapReportService";
import { Play, Bookmark, CheckSquare } from "lucide-react";

interface GapActionButtonsProps {
  gapId?: string;
  conceptId: string;
  isGap?: boolean;
  isResolved?: boolean;
}

export default function GapActionButtons({
  gapId,
  conceptId,
  isGap = false,
  isResolved = false,
}: GapActionButtonsProps) {
  const { toast } = useToast();
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  async function handlePractice() {
    setLoadingAction("practice");
    try {
      if (gapId) {
        await practiceGap(gapId);
      }
      toast({
        title: "PRACTICE SESSION CREATED",
        description: "Targeted interactive practice module initiated.",
      });
    } catch (error) {
      toast({
        title: "PRACTICE SESSION FAILED",
        description: "Could not initialize practice session. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleSave() {
    setLoadingAction("save");
    try {
      if (gapId) {
        await saveGapForLater(gapId);
      }
      toast({
        title: "SAVED FOR LATER",
        description: "Added to your personalized learning backlog.",
      });
    } catch (error) {
      toast({
        title: "COULDN'T SAVE. TRY AGAIN.",
        description: "Failed to persist gap into review list.",
        variant: "destructive",
      });
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleReview() {
    setLoadingAction("review");
    try {
      await markConceptForReview(conceptId);
      toast({
        title: "MARKED FOR REVIEW",
        description: "Concept scheduled for periodic retention verification.",
      });
    } catch (error) {
      toast({
        title: "ACTION FAILED",
        description: "Could not mark concept for review.",
        variant: "destructive",
      });
    } finally {
      setLoadingAction(null);
    }
  }

  if (isGap) {
    return (
      <div className="flex flex-col gap-2.5 pt-2">
        <KeycapButton
          variant="gap"
          onClick={handlePractice}
          loading={loadingAction === "practice"}
          className="w-full"
        >
          <Play className="h-3.5 w-3.5 mr-1 fill-current" />
          PRACTICE GAP ▶
        </KeycapButton>

        <KeycapButton
          variant="default"
          onClick={handleSave}
          loading={loadingAction === "save"}
          className="w-full"
        >
          <Bookmark className="h-3.5 w-3.5 mr-1" />
          SAVE FOR LATER
        </KeycapButton>
      </div>
    );
  }

  if (isResolved) {
    return (
      <div className="flex flex-col gap-2.5 pt-2">
        <KeycapButton
          variant="resolve"
          onClick={handleReview}
          loading={loadingAction === "review"}
          className="w-full"
        >
          <CheckSquare className="h-3.5 w-3.5 mr-1" />
          MARK FOR REVIEW
        </KeycapButton>
      </div>
    );
  }

  // Strong / Developing default state
  return (
    <div className="flex flex-col gap-2.5 pt-2">
      <KeycapButton
        variant="default"
        onClick={handlePractice}
        loading={loadingAction === "practice"}
        className="w-full"
      >
        <Play className="h-3.5 w-3.5 mr-1 fill-current" />
        EXPLORE DEEPER
      </KeycapButton>
    </div>
  );
}
