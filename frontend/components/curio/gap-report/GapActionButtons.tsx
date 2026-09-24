"use client";

import React, { useState } from "react";
import { KeycapButton } from "@/components/curio/KeycapButton";

export interface GapActionButtonsProps {
  gapId: string;
  onPracticeGap: (gapId: string) => Promise<void>;
  onSaveForLater: (gapId: string) => Promise<void>;
  onMarkForReview: (gapId: string) => Promise<void>;
}

export function GapActionButtons({
  gapId,
  onPracticeGap,
  onSaveForLater,
  onMarkForReview,
}: GapActionButtonsProps) {
  const [loadingPractice, setLoadingPractice] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [loadingReview, setLoadingReview] = useState(false);

  const handlePractice = async () => {
    setLoadingPractice(true);
    try {
      await onPracticeGap(gapId);
    } finally {
      setLoadingPractice(false);
    }
  };

  const handleSave = async () => {
    setLoadingSave(true);
    try {
      await onSaveForLater(gapId);
    } finally {
      setLoadingSave(false);
    }
  };

  const handleReview = async () => {
    setLoadingReview(true);
    try {
      await onMarkForReview(gapId);
    } finally {
      setLoadingReview(false);
    }
  };

  return (
    <div className="space-y-2 w-full pt-1">
      <KeycapButton
        variant="gap"
        size="md"
        loading={loadingPractice}
        loadingText="STARTING..."
        onClick={handlePractice}
        className="w-full justify-center"
      >
        PRACTICE GAP ▶
      </KeycapButton>

      <div className="grid grid-cols-2 gap-2">
        <KeycapButton
          variant="ghost"
          size="sm"
          loading={loadingSave}
          loadingText="SAVING..."
          onClick={handleSave}
          className="w-full text-[11px]"
        >
          SAVE FOR LATER
        </KeycapButton>

        <KeycapButton
          variant="ghost"
          size="sm"
          loading={loadingReview}
          loadingText="MARKING..."
          onClick={handleReview}
          className="w-full text-[11px]"
        >
          MARK FOR REVIEW
        </KeycapButton>
      </div>
    </div>
  );
}
