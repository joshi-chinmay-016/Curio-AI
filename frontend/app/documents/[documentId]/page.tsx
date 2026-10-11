"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  File,
  ArrowLeft,
  Calendar,
  Layers,
  HardDrive,
  Hash,
  Sparkles,
  AlertCircle,
  RefreshCw,
  Trash2,
  CheckCircle2,
  Clock,
  ExternalLink,
  BookOpen,
  HelpCircle,
  Cpu,
} from "lucide-react";
import { DocumentItem } from "@/types/document";
import {
  getDocument,
  processDocument,
  formatFileSize,
  formatDocumentStatus,
} from "@/services/documentService";
import { startSession } from "@/services/sessionService";
import { curioToast } from "@/components/curio/CurioToast";
import { DeleteDocumentDialog } from "@/components/curio/documents/DeleteDocumentDialog";
import { CurioNav } from "@/components/curio/CurioNav";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = Array.isArray(params?.documentId)
    ? params.documentId[0]
    : (params?.documentId as string);

  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);
  const [isStartingSession, setIsStartingSession] = useState<boolean>(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState<boolean>(false);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDoc = useCallback(async (quiet = false) => {
    if (!documentId) return;
    if (!quiet) setLoading(true);
    setError(null);
    try {
      const data = await getDocument(documentId);
      setDocument(data);
    } catch (err: any) {
      console.error("Failed to load document:", err);
      const msg = err?.message || "Could not retrieve document details.";
      setError(msg);
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    fetchDoc();
  }, [fetchDoc]);

  // Handle polling when document is in PROCESSING status
  useEffect(() => {
    if (document?.status === "PROCESSING") {
      pollingRef.current = setInterval(() => {
        fetchDoc(true);
      }, 3000);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [document?.status, fetchDoc]);

  const handleProcess = async () => {
    if (!document) return;
    setIsProcessingAction(true);
    try {
      const updated = await processDocument(document.document_id);
      setDocument(updated);
      curioToast.info("Text processing started", "Extracting passages and creating search chunks.");
    } catch (err: any) {
      curioToast.error("Processing failed", err?.message || "Could not trigger text extraction.");
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleStartLearning = async () => {
    if (!document) return;
    setIsStartingSession(true);
    try {
      // Clean up extension from topic name for conversational display
      const topic = document.filename.replace(/\.[^/.]+$/, "").trim() || "Document Learning";
      const session = await startSession(topic, {
        sourceType: "DOCUMENT",
        documentId: document.document_id,
      });

      curioToast.success("Session Created", `Learning grounded in ${document.filename}`);
      router.push(`/session/${session.sessionId}`);
    } catch (err: any) {
      curioToast.error("Failed to start session", err?.message || "Could not initialize document session.");
      setIsStartingSession(false);
    }
  };

  const getFileExtension = (name: string) => {
    const parts = name.split(".");
    return parts.length > 1 ? parts.pop()?.toUpperCase() : "DOC";
  };

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col font-sans selection:bg-cobalt selection:text-white">
      <CurioNav />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Back breadcrumb */}
        <div className="mb-6">
          <Link
            href="/documents"
            className="inline-flex items-center gap-2 text-xs font-mono tracking-wider uppercase text-slate-500 hover:text-navy transition-colors group"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            Back to My Documents
          </Link>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="space-y-6 animate-pulse">
            <div className="h-32 bg-white rounded-2xl border border-slate-200/80 p-6" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="h-44 bg-white rounded-2xl border border-slate-200/80 md:col-span-2" />
              <div className="h-44 bg-white rounded-2xl border border-slate-200/80" />
            </div>
          </div>
        )}

        {/* Error / Not found state */}
        {!loading && error && (
          <div className="bg-white rounded-2xl border border-rose-200 shadow-sm p-8 text-center max-w-md mx-auto my-12">
            <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto mb-4 text-rose-600">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-navy font-sora mb-2">Document Unavailable</h2>
            <p className="text-sm text-slate-600 mb-6 leading-relaxed">
              {error.includes("404") || error.includes("Not Found")
                ? "This document may have been deleted or does not belong to your account."
                : error}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => fetchDoc()}
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry
              </button>
              <Link
                href="/documents"
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors"
              >
                Go to Library
              </Link>
            </div>
          </div>
        )}

        {/* Document loaded */}
        {!loading && document && (
          <div className="space-y-8">
            {/* Header banner card */}
            {(() => {
              const statusInfo = formatDocumentStatus(document.status);
              const ext = getFileExtension(document.filename);

              return (
                <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-8 relative overflow-hidden">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
                    <div className="flex items-start gap-4 sm:gap-5">
                      <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-xl bg-cobalt/5 border border-cobalt/20 flex flex-col items-center justify-center text-cobalt flex-shrink-0 shadow-sm">
                        {ext === "PDF" ? (
                          <FileText className="w-6 h-6 sm:w-7 sm:h-7" />
                        ) : (
                          <File className="w-6 h-6 sm:w-7 sm:h-7" />
                        )}
                        <span className="text-[10px] font-mono font-bold uppercase tracking-wider mt-0.5">
                          {ext}
                        </span>
                      </div>

                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2.5">
                          <h1 className="text-xl sm:text-2xl font-bold font-sora text-navy break-all">
                            {document.filename}
                          </h1>
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${statusInfo.badgeClass}`}
                          >
                            {statusInfo.isReady && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                            {statusInfo.isProcessing && (
                              <RefreshCw className="w-3 h-3 text-amber-600 animate-spin" />
                            )}
                            {statusInfo.isFailed && <AlertCircle className="w-3 h-3 text-rose-600" />}
                            {statusInfo.label}
                          </span>
                        </div>

                        <p className="text-xs sm:text-sm text-slate-500 font-sans">
                          {statusInfo.description}
                        </p>
                      </div>
                    </div>

                    {/* Quick header actions */}
                    <div className="flex items-center gap-2 self-end sm:self-start flex-shrink-0">
                      <button
                        onClick={() => fetchDoc()}
                        title="Refresh metadata"
                        className="p-2.5 rounded-xl border border-slate-200 hover:border-slate-300 text-slate-600 hover:text-navy hover:bg-slate-50 transition-colors"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteModalOpen(true)}
                        title="Delete document"
                        className="p-2.5 rounded-xl border border-rose-200 hover:border-rose-300 text-rose-600 hover:bg-rose-50/80 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Primary Workflow Bar */}
                  <div className="mt-8 pt-6 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      {statusInfo.isReady && (
                        <p className="text-xs font-mono text-emerald-700 font-medium">
                          Grounded learning engine active. Curio will use this document as authoritative context.
                        </p>
                      )}
                      {statusInfo.isProcessing && (
                        <p className="text-xs font-mono text-amber-700 font-medium flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                          Processing chunks... This page will update automatically.
                        </p>
                      )}
                      {statusInfo.isFailed && (
                        <p className="text-xs font-mono text-rose-700 font-medium">
                          Text extraction failed. Try processing again or re-uploading the file.
                        </p>
                      )}
                      {document.status === "UPLOADED" && (
                        <p className="text-xs font-mono text-cyan-800 font-medium">
                          File uploaded. Text extraction required to enable AI grounding.
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      {statusInfo.isReady && (
                        <button
                          onClick={handleStartLearning}
                          disabled={isStartingSession}
                          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-cobalt text-white font-medium text-sm hover:bg-cobalt/90 shadow-sm hover:shadow transition-all disabled:opacity-50"
                        >
                          <Sparkles className="w-4 h-4 text-ice" />
                          {isStartingSession ? "Initializing Session..." : "Learn from this Document"}
                        </button>
                      )}

                      {(document.status === "UPLOADED" || statusInfo.isFailed) && (
                        <button
                          onClick={handleProcess}
                          disabled={isProcessingAction}
                          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-navy text-white font-medium text-sm hover:bg-navy/90 transition-all disabled:opacity-50"
                        >
                          <Cpu className="w-4 h-4 text-cyan-400" />
                          {isProcessingAction
                            ? "Triggering..."
                            : statusInfo.isFailed
                            ? "Retry Extraction"
                            : "Process Text"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Metadata and Grounding Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Left 2 Cols: Document Metadata */}
              <div className="md:col-span-2 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-7 space-y-6">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <h2 className="text-sm font-mono uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-2">
                    <FileText className="w-4 h-4 text-cobalt" />
                    Document Specifications
                  </h2>
                  <span className="text-xs font-mono text-slate-400">Validated Backend Schema</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/60">
                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">
                      <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                      File Size
                    </div>
                    <div className="text-lg font-bold font-sora text-navy">
                      {formatFileSize(document.file_size)}
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-1">
                      {document.file_size.toLocaleString()} bytes
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/60">
                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      Retrieval Chunks
                    </div>
                    <div className="text-lg font-bold font-sora text-navy">
                      {document.chunk_count}
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-1">
                      {document.chunk_count > 0
                        ? "Indexed for RAG semantic search"
                        : "Awaiting text processing"}
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/60">
                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">
                      <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                      Page Count
                    </div>
                    <div className="text-lg font-bold font-sora text-navy">
                      {document.page_count !== null && document.page_count !== undefined
                        ? `${document.page_count} ${document.page_count === 1 ? "page" : "pages"}`
                        : "Single stream / N/A"}
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-1">
                      Extracted from container
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/60">
                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      Uploaded At
                    </div>
                    <div className="text-sm font-semibold font-sora text-navy mt-1">
                      {new Date(document.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                      {new Date(document.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
                    <span>MIME TYPE</span>
                    <span className="text-navy font-medium">{document.mime_type}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
                    <span>DOCUMENT ID</span>
                    <span className="text-navy font-mono text-[11px] bg-slate-100 px-2 py-0.5 rounded">
                      {document.document_id}
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Col: Feynman Grounding Intelligence */}
              <div className="bg-gradient-to-br from-navy to-slate-900 rounded-2xl border border-navy shadow-sm p-6 sm:p-7 text-white flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-cyan-400 font-semibold mb-4">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    Feynman Grounding
                  </div>
                  <h3 className="text-base font-bold font-sora text-white mb-2">
                    How Curio Uses Your Notes
                  </h3>
                  <p className="text-xs text-slate-300 leading-relaxed mb-6 font-sans">
                    When you link this document to a learning session, Curio anchors its inquiry directly in your material.
                  </p>

                  <div className="space-y-4">
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                      <div className="text-xs font-mono text-cyan-300 font-semibold mb-1">
                        In Student Mode
                      </div>
                      <p className="text-[11px] text-slate-300 leading-relaxed">
                        Curio asks thoughtful questions about key concepts, definitions, and relationships in this document.
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                      <div className="text-xs font-mono text-amber-300 font-semibold mb-1">
                        In Teacher Mode
                      </div>
                      <p className="text-[11px] text-slate-300 leading-relaxed">
                        Curio cross-checks your explanations against the document to identify specific misconceptions and missing ideas.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>GROUNDING STATUS</span>
                  <span className={document.status === "PROCESSED" ? "text-emerald-400" : "text-amber-400"}>
                    {document.status === "PROCESSED" ? "READY" : "PENDING EXTRACTION"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Delete Confirmation Modal */}
      {document && (
        <DeleteDocumentDialog
          isOpen={deleteModalOpen}
          document={document}
          onClose={() => setDeleteModalOpen(false)}
          onDeleted={() => {
            setDeleteModalOpen(false);
            router.push("/documents");
          }}
        />
      )}
    </div>
  );
}
