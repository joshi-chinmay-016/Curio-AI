"use client";

import React from "react";
import { KeycapButton } from "@/components/curio/KeycapButton";

export interface FinishDialogProps {
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function FinishDialog({ isOpen, onCancel, onConfirm }: FinishDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/30 backdrop-blur-[1px] p-4">
      <div className="w-full max-w-md bg-white border-2 border-navy rounded-none shadow-[8px_8px_0_0_#0F2B4A] p-6 text-navy">
        <h3 className="font-heading text-lg font-bold mb-2">
          End this session?
        </h3>
        <p className="font-sans text-sm text-navy/80 mb-6">
          Curio will analyze your explanations, identify your exact knowledge gaps, and generate your isometric Gap Report.
        </p>
        <div className="flex items-center justify-end gap-3">
          <KeycapButton
            variant="ghost"
            size="sm"
            onClick={onCancel}
          >
            [CANCEL]
          </KeycapButton>
          <KeycapButton
            variant="navy"
            size="sm"
            onClick={onConfirm}
          >
            [END SESSION →]
          </KeycapButton>
        </div>
      </div>
    </div>
  );
}
