"use client";

import React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowRight, BookOpen } from "lucide-react";
import { useGapReport } from "@/hooks/useGapReport";
import { GapReportHeader } from "@/components/curio/gap-report/GapReportHeader";
import { GapReportSummary } from "@/components/curio/gap-report/GapReportSummary";
import { IsometricKnowledgeMap } from "@/components/curio/gap-report/IsometricKnowledgeMap";
import { TopicSwitcher } from "@/components/curio/gap-report/TopicSwitcher";
import { SelectedConceptPanel } from "@/components/curio/gap-report/SelectedConceptPanel";
import { EvidenceViewer } from "@/components/curio/gap-report/EvidenceViewer";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";

export default function GapReportPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = (params?.id as string) || "session_mock_bs";

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
    resetMap,
    handlePracticeGap,
    handleSaveForLater,
    handleMarkForReview,
  } = useGapReport(sessionId);

  if (isLoading || !report) {
    return (
      <div className="min-h-screen bg-ice text-navy flex items-center justify-center">
        <div className="font-mono text-sm uppercase tracking-widest text-navy flex items-center gap-2">
          <span className="animate-spin text-cobalt text-lg">◈</span>
          LOADING GAP REPORT...
        </div>
      </div>
    );
  }

  const handleSelectRelatedConcept = (conceptId: string) => {
    const target = report.concepts.find((c) => c.id === conceptId);
    if (target) {
      setSelectedConcept(target);
    }
  };

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Header */}
      <GapReportHeader
        topicName={report.topicName}
        sessionId={report.sessionId}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 md:px-8 py-6">
        {/* Summary Strip (4 Cards) */}
        <GapReportSummary report={report} />

        {/* Topic Switcher Strip */}
        {report.availableTopics && report.availableTopics.length > 0 && (
          <TopicSwitcher
            topics={report.availableTopics}
            currentTopicId={report.sessionId}
            onSelectTopic={(newSessionId) => {
              router.push(`/session/${newSessionId}/report`);
            }}
          />
        )}

        {/* 2-Column Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (65% on desktop): Isometric Knowledge Map */}
          <div className="lg:col-span-8 flex flex-col">
            <IsometricKnowledgeMap
              report={report}
              selectedConcept={selectedConcept}
              isExploded={isExploded}
              focusGaps={focusGaps}
              onSelectConcept={setSelectedConcept}
              onToggleExplode={() => setIsExploded((prev) => !prev)}
              onReset={resetMap}
              onToggleFocusGaps={() => setFocusGaps((prev) => !prev)}
              onShowAll={() => {
                setFocusGaps(false);
              }}
            />
          </div>

          {/* Right Column (35% on desktop): Selected Concept Panel */}
          <div className="lg:col-span-4 flex flex-col h-full">
            <SelectedConceptPanel
              concept={selectedConcept}
              report={report}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              onSelectRelatedConcept={handleSelectRelatedConcept}
              onViewEvidence={(gap) => setEvidenceModalOpen(true, gap)}
              onPracticeGap={handlePracticeGap}
              onSaveForLater={handleSaveForLater}
              onMarkForReview={handleMarkForReview}
            />
          </div>
        </div>

        {/* Recommended Next Steps Footer Strip */}
        <section className="mt-10 mb-8 bg-white border border-fog rounded-[6px] p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <span className="font-mono text-xs uppercase tracking-wider text-navy/50 font-bold block mb-2">
                RECOMMENDED NEXT STEPS
              </span>
              <ul className="space-y-1.5 font-sans text-sm text-navy/85">
                {report.recommendedNextSteps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="font-mono text-xs font-bold text-cobalt shrink-0 mt-0.5">
                      0{idx + 1}.
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex items-center gap-3 shrink-0 flex-wrap">
              {report.knowledgeGaps > 0 && (
                <KeycapButton
                  variant="gap"
                  size="md"
                  onClick={() => {
                    if (report.gaps[0]) {
                      handlePracticeGap(report.gaps[0].id);
                    }
                  }}
                >
                  PRACTICE GAPS ▶
                </KeycapButton>
              )}
              <Link href="/topics">
                <KeycapButton variant="navy" size="md">
                  START NEW SESSION →
                </KeycapButton>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Evidence Viewer Modal */}
      <EvidenceViewer
        isOpen={evidenceModalOpen}
        gap={activeEvidenceGap}
        onClose={() => setEvidenceModalOpen(false, null)}
      />
    </div>
  );
}
