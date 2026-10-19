"use client";

import React, { useState, useEffect } from "react";
import {
  AudioLearningMode,
  AudioSessionConfig,
  DifficultyOrdering,
} from "@/types/audioLearning";
import { KeycapButton } from "@/components/curio/KeycapButton";
import {
  BookOpen,
  GraduationCap,
  FileText,
  Upload,
  CheckCircle2,
  Clock,
  Sparkles,
  Layers,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { listDocuments, uploadDocument, processDocument } from "@/services/documentService";
import { DocumentItem } from "@/types/document";
import { curioToast } from "@/components/curio/CurioToast";

interface AudioSessionSetupProps {
  onStartSession: (config: AudioSessionConfig) => Promise<void>;
  isStarting?: boolean;
}

const DEFAULT_TOPICS = [
  "CAP Theorem & Distributed Systems",
  "Transformer Multi-Head Self-Attention",
  "TCP 3-Way Handshake & Congestion Control",
  "Database Indexing with B-Trees",
  "The Feynman Technique in Science",
];

export function AudioSessionSetup({
  onStartSession,
  isStarting = false,
}: AudioSessionSetupProps) {
  const [selectedMode, setSelectedMode] = useState<AudioLearningMode>("STUDENT");
  const [topic, setTopic] = useState("CAP Theorem & Distributed Systems");
  const [sourceType, setSourceType] = useState<"GENERAL" | "DOCUMENT">("GENERAL");
  const [selectedDocId, setSelectedDocId] = useState<string | undefined>();
  const [difficultyOrder, setDifficultyOrder] = useState<DifficultyOrdering>("EASY_TO_HARD");

  // Document state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function fetchDocs() {
      setLoadingDocs(true);
      try {
        const res = await listDocuments(1, 20);
        if (mounted && res?.documents) {
          setDocuments(res.documents);
        }
      } catch (err) {
        console.warn("Failed to load documents:", err);
      } finally {
        if (mounted) setLoadingDocs(false);
      }
    }
    fetchDocs();
    return () => {
      mounted = false;
    };
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingDoc(true);
    try {
      const doc = await uploadDocument(file);
      curioToast.info("DOCUMENT UPLOADED", "Processing text extraction...");
      // Trigger processing
      const processed = await processDocument(doc.document_id);
      setDocuments((prev) => [processed, ...prev]);
      setSelectedDocId(processed.document_id);
      setSourceType("DOCUMENT");
      curioToast.success("READY FOR GROUNDING", `Document "${file.name}" indexed.`);
    } catch (err: any) {
      curioToast.error("UPLOAD FAILED", err.message || "Failed to upload document.");
    } finally {
      setUploadingDoc(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      curioToast.error("TOPIC REQUIRED", "Please enter or select a topic.");
      return;
    }

    const selectedDoc = documents.find((d) => d.document_id === selectedDocId);

    await onStartSession({
      mode: selectedMode,
      topic: topic.trim(),
      sourceType: sourceType,
      documentId: sourceType === "DOCUMENT" ? selectedDocId : undefined,
      documentName: sourceType === "DOCUMENT" ? selectedDoc?.filename : undefined,
      difficultyOrder: selectedMode === "PROFESSOR" ? difficultyOrder : undefined,
      maxConsecutiveUnanswered: 3,
    });
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-6 md:p-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-white border border-fog rounded-full text-xs font-mono font-bold uppercase tracking-wider text-navy/70 mb-3 shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-gap-orange" />
          SESSION CONFIGURATION
        </div>
        <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-navy tracking-tight">
          Configure Your Audio Learning Session
        </h1>
        <p className="font-sans text-sm text-navy/60 mt-1 max-w-lg mx-auto">
          Choose your animated AI companion, choose a topic or upload document notes, and speak naturally.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Step 1: Mode Selection */}
        <div>
          <label className="font-mono text-xs uppercase font-bold text-navy/60 block mb-3 tracking-wider">
            1. SELECT AUDIO LEARNING COMPANION
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Student Mode Card */}
            <div
              onClick={() => setSelectedMode("STUDENT")}
              className={`p-5 rounded-[10px] border-2 cursor-pointer transition-all ${
                selectedMode === "STUDENT"
                  ? "bg-white border-navy shadow-[4px_4px_0_0_#0F2B4A] ring-2 ring-cobalt/30"
                  : "bg-white/70 border-fog hover:border-navy/40"
              }`}
            >
              <div className="flex items-start gap-4">
                <img
                  src="/characters/student.png"
                  alt="Student Character"
                  className="w-16 h-20 object-cover rounded-[8px] border border-fog shadow-xs shrink-0"
                />
                <div className="min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-heading text-base font-bold text-navy">
                      Student Mode
                    </span>
                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold rounded-full">
                      TEACHING
                    </span>
                  </div>
                  <p className="font-sans text-xs text-navy/70 leading-relaxed">
                    Teach a curious young student aloud. When you struggle, a female teacher appears to help you recover.
                  </p>
                </div>
              </div>
            </div>

            {/* Professor Mode Card */}
            <div
              onClick={() => setSelectedMode("PROFESSOR")}
              className={`p-5 rounded-[10px] border-2 cursor-pointer transition-all ${
                selectedMode === "PROFESSOR"
                  ? "bg-white border-navy shadow-[4px_4px_0_0_#0F2B4A] ring-2 ring-navy/30"
                  : "bg-white/70 border-fog hover:border-navy/40"
              }`}
            >
              <div className="flex items-start gap-4">
                <img
                  src="/characters/professor.png"
                  alt="Professor Character"
                  className="w-16 h-20 object-cover rounded-[8px] border border-fog shadow-xs shrink-0"
                />
                <div className="min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-heading text-base font-bold text-navy">
                      Professor Mode
                    </span>
                    <span className="px-2 py-0.5 bg-navy/10 text-navy border border-navy/20 text-[10px] font-mono font-bold rounded-full">
                      INTERVIEW
                    </span>
                  </div>
                  <p className="font-sans text-xs text-navy/70 leading-relaxed">
                    Strict oral exam simulation. The professor asks questions, tests under pressure, and evaluates depth.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Step 2: Topic Selection */}
        <div>
          <label className="font-mono text-xs uppercase font-bold text-navy/60 block mb-2 tracking-wider">
            2. TOPIC OR CONCEPT TO PRACTICE
          </label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Distributed Consensus, QuickSort, Photosynthesis..."
            className="w-full p-3 bg-white border-2 border-navy rounded-[8px] font-sans text-sm md:text-base text-navy shadow-xs focus:outline-none focus:ring-2 focus:ring-cobalt"
          />

          {/* Quick suggestions */}
          <div className="flex flex-wrap items-center gap-2 mt-2.5">
            <span className="font-mono text-[10px] uppercase font-bold text-navy/40">
              Suggestions:
            </span>
            {DEFAULT_TOPICS.map((t, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setTopic(t)}
                className="px-2.5 py-1 bg-white border border-fog hover:border-navy rounded-[4px] font-mono text-[11px] text-navy/70 hover:text-navy transition-colors cursor-pointer"
              >
                {t.split("&")[0].trim()}
              </button>
            ))}
          </div>
        </div>

        {/* Step 3: Document Grounding (Optional) */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="font-mono text-xs uppercase font-bold text-navy/60 tracking-wider">
              3. ATTACH KNOWLEDGE DOCUMENT (OPTIONAL RAG)
            </label>
            <div className="flex items-center gap-2 text-xs font-mono">
              <button
                type="button"
                onClick={() => {
                  setSourceType("GENERAL");
                  setSelectedDocId(undefined);
                }}
                className={`px-2 py-0.5 rounded cursor-pointer ${
                  sourceType === "GENERAL" ? "bg-navy text-white font-bold" : "text-navy/50 hover:text-navy"
                }`}
              >
                GENERAL KNOWLEDGE
              </button>
              <button
                type="button"
                onClick={() => setSourceType("DOCUMENT")}
                className={`px-2 py-0.5 rounded cursor-pointer ${
                  sourceType === "DOCUMENT" ? "bg-navy text-white font-bold" : "text-navy/50 hover:text-navy"
                }`}
              >
                DOCUMENT GROUNDED
              </button>
            </div>
          </div>

          {sourceType === "DOCUMENT" && (
            <div className="bg-white border-2 border-navy rounded-[8px] p-4 shadow-xs space-y-4">
              {/* Document upload drop target */}
              <div className="flex items-center justify-between gap-4 p-3 bg-ice/60 border border-dashed border-fog rounded-[6px]">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white rounded-md text-cobalt border border-fog">
                    <Upload className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-heading text-xs font-bold text-navy block">
                      Upload PDF, TXT, or DOCX
                    </span>
                    <span className="font-mono text-[10px] text-navy/50">
                      Up to 10 MB per file
                    </span>
                  </div>
                </div>

                <label className="cursor-pointer">
                  <span className="px-3 py-1.5 bg-white border border-navy rounded-[4px] font-mono text-xs font-bold text-navy hover:bg-ice transition-colors inline-flex items-center gap-1.5 shadow-xs">
                    {uploadingDoc ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        PROCESSING...
                      </>
                    ) : (
                      "CHOOSE FILE"
                    )}
                  </span>
                  <input
                    type="file"
                    accept=".pdf,.txt,.docx"
                    onChange={handleFileUpload}
                    disabled={uploadingDoc}
                    className="hidden"
                  />
                </label>
              </div>

              {/* Existing documents list */}
              {loadingDocs ? (
                <div className="p-4 text-center font-mono text-xs text-navy/40 animate-pulse">
                  LOADING DOCUMENTS...
                </div>
              ) : documents.length === 0 ? (
                <div className="p-4 text-center font-sans text-xs text-navy/50">
                  No documents found. Upload notes or syllabus above to ground the session.
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {documents.map((doc) => {
                    const isSelected = selectedDocId === doc.document_id;
                    const isReady = doc.status === "PROCESSED";
                    return (
                      <div
                        key={doc.document_id}
                        onClick={() => {
                          if (isReady) setSelectedDocId(doc.document_id);
                        }}
                        className={`p-2.5 rounded-[6px] border flex items-center justify-between gap-3 transition-colors ${
                          isSelected
                            ? "bg-cobalt/5 border-cobalt text-navy font-medium"
                            : isReady
                            ? "bg-white border-fog hover:border-navy/40 cursor-pointer"
                            : "bg-fog/30 border-fog text-navy/40 cursor-not-allowed"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <FileText className={`w-4 h-4 shrink-0 ${isSelected ? "text-cobalt" : "text-navy/40"}`} />
                          <span className="font-sans text-xs truncate font-medium">
                            {doc.filename}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {isReady ? (
                            <span className="inline-flex items-center gap-1 font-mono text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                              <CheckCircle2 className="w-3 h-3" /> READY
                            </span>
                          ) : (
                            <span className="font-mono text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                              {doc.status}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Step 4: Professor Mode Difficulty Ordering */}
        {selectedMode === "PROFESSOR" && (
          <div>
            <label className="font-mono text-xs uppercase font-bold text-navy/60 block mb-2 tracking-wider">
              4. PROFESSOR QUESTION DIFFICULTY PROGRESSION
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: "EASY_TO_HARD", label: "Easy to Hard", desc: "Gradual ramp-up" },
                { id: "HARD_TO_EASY", label: "Hard to Easy", desc: "High pressure start" },
                { id: "MIXED", label: "Mixed Difficulty", desc: "Randomized stress test" },
              ].map((diff) => (
                <div
                  key={diff.id}
                  onClick={() => setDifficultyOrder(diff.id as DifficultyOrdering)}
                  className={`p-3 rounded-[6px] border-2 cursor-pointer transition-all text-center ${
                    difficultyOrder === diff.id
                      ? "bg-white border-navy shadow-[2px_2px_0_0_#0F2B4A] font-bold"
                      : "bg-white/70 border-fog text-navy/60"
                  }`}
                >
                  <span className="font-heading text-xs block">{diff.label}</span>
                  <span className="font-mono text-[10px] text-navy/50">{diff.desc}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Submit Action */}
        <div className="pt-4 flex items-center justify-center">
          <KeycapButton
            type="submit"
            disabled={isStarting || (sourceType === "DOCUMENT" && !selectedDocId)}
            variant="navy"
            size="lg"
            className="w-full sm:w-auto px-8"
          >
            {isStarting ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                INITIALIZING AUDIO ENGINE...
              </span>
            ) : (
              <span className="inline-flex items-center gap-2 text-base font-bold">
                <Sparkles className="w-5 h-5 text-gap-orange" />
                START AUDIO LEARNING SESSION →
              </span>
            )}
          </KeycapButton>
        </div>
      </form>
    </div>
  );
}
