"use client";

import { useEffect, useCallback } from "react";
import { useReportStore } from "@/stores/reportStore";
import { curioToast } from "@/components/curio/CurioToast";
import { saveToPracticeQueue } from "@/services/historyService";

export function useGapReport(sessionId?: string) {
  const {
    report,
    selectedConcept,
    activeTab,
    isExploded,
    focusGaps,
    isLoading,
    evidenceModalOpen,
    activeEvidenceGap,
    setSelectedConcept,
    setActiveTab,
    setIsExploded,
    setFocusGaps,
    setEvidenceModalOpen,
    loadReport,
    resetMap,
  } = useReportStore();

  // Load report on mount or when sessionId changes
  useEffect(() => {
    loadReport(sessionId);
  }, [sessionId, loadReport]);

  // Keyboard navigation shortcuts (R, F, ESC)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts if inside input or textarea
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }

      if (e.key === "Escape") {
        if (evidenceModalOpen) {
          setEvidenceModalOpen(false);
        } else if (selectedConcept) {
          setSelectedConcept(null);
        }
      } else if (e.key === "r" || e.key === "R") {
        resetMap();
        curioToast.info("MAP RESET TO DEFAULT STACK.");
      } else if (e.key === "f" || e.key === "F") {
        setFocusGaps((prev) => !prev);
        curioToast.info("TOGGLED GAP FOCUS MODE.");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    evidenceModalOpen,
    resetMap,
    selectedConcept,
    setEvidenceModalOpen,
    setFocusGaps,
    setSelectedConcept,
  ]);

  // Action: Practice Gap
  const handlePracticeGap = useCallback(
    async (gapId: string) => {
      const gap = report?.gaps.find((g) => g.id === gapId);
      if (!gap) return;

      // Simulated network action
      await new Promise((res) => setTimeout(res, 600));
      curioToast.success("PRACTICE SESSION CREATED.", `Targeting ${gap.title}`);
    },
    [report]
  );

  // Action: Save For Later
  const handleSaveForLater = useCallback(
    async (gapId: string) => {
      const gap = report?.gaps.find((g) => g.id === gapId);
      if (!gap) return;

      try {
        await saveToPracticeQueue({
          gapId: gap.id,
          conceptName: gap.title,
          topicName: report?.topicName || "Binary Search",
          severity: gap.severity,
        });
        curioToast.success("SAVED FOR LATER.", "Added to your practice queue.");
      } catch {
        curioToast.error("COULDN'T SAVE. TRY AGAIN.");
      }
    },
    [report]
  );

  // Action: Mark For Review
  const handleMarkForReview = useCallback(async (gapId: string) => {
    await new Promise((res) => setTimeout(res, 400));
    curioToast.info("MARKED FOR REVIEW.");
  }, []);

  return {
    report,
    selectedConcept,
    activeTab,
    isExploded,
    focusGaps,
    isLoading,
    evidenceModalOpen,
    activeEvidenceGap,
    setSelectedConcept,
    setActiveTab,
    setIsExploded,
    setFocusGaps,
    setEvidenceModalOpen,
    resetMap,
    handlePracticeGap,
    handleSaveForLater,
    handleMarkForReview,
  };
}
