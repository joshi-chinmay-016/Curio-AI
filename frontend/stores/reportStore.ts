import { create } from "zustand";
import { GapReport, ConceptCell, Gap } from "@/types/gapReport";
import { getGapReport } from "@/services/gapReportService";

interface ReportStoreState {
  report: GapReport | null;
  selectedConcept: ConceptCell | null;
  activeTab: "overview" | "gap_details";
  isExploded: boolean;
  focusGaps: boolean;
  isLoading: boolean;
  evidenceModalOpen: boolean;
  activeEvidenceGap: Gap | null;

  setReport: (report: GapReport | null) => void;
  setSelectedConcept: (concept: ConceptCell | null) => void;
  setActiveTab: (tab: "overview" | "gap_details") => void;
  setIsExploded: (exploded: boolean | ((prev: boolean) => boolean)) => void;
  setFocusGaps: (focus: boolean | ((prev: boolean) => boolean)) => void;
  setEvidenceModalOpen: (open: boolean, gap?: Gap | null) => void;
  loadReport: (sessionId?: string) => Promise<void>;
  resetMap: () => void;
}

export const useReportStore = create<ReportStoreState>((set, get) => ({
  report: null,
  selectedConcept: null,
  activeTab: "overview",
  isExploded: false,
  focusGaps: false,
  isLoading: false,
  evidenceModalOpen: false,
  activeEvidenceGap: null,

  setReport: (report) => set({ report }),
  setSelectedConcept: (selectedConcept) => {
    const isGap =
      selectedConcept?.status === "GAP" ||
      selectedConcept?.status === "MISCONCEPTION";
    set({
      selectedConcept,
      activeTab: isGap ? "gap_details" : "overview",
      isExploded: true, // auto-explode if collapsed on cell select
    });
  },
  setActiveTab: (activeTab) => set({ activeTab }),
  setIsExploded: (action) =>
    set((state) => ({
      isExploded: typeof action === "function" ? action(state.isExploded) : action,
    })),
  setFocusGaps: (action) =>
    set((state) => ({
      focusGaps: typeof action === "function" ? action(state.focusGaps) : action,
    })),
  setEvidenceModalOpen: (open, gap = null) =>
    set({ evidenceModalOpen: open, activeEvidenceGap: gap }),

  loadReport: async (sessionId?: string) => {
    set({ isLoading: true });
    try {
      const data = await getGapReport(sessionId);
      set({
        report: data,
        selectedConcept: null,
        isExploded: false,
        focusGaps: false,
      });
    } catch (err) {
      console.error("Failed to load gap report:", err);
    } finally {
      set({ isLoading: false });
    }
  },

  resetMap: () => {
    set({
      selectedConcept: null,
      isExploded: false,
      focusGaps: false,
      activeTab: "overview",
    });
  },
}));
