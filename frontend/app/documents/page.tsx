"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FileText,
  Upload,
  Sparkles,
  BookOpen,
  ArrowRight,
  RotateCcw,
  LogOut,
  AlertCircle,
  Plus,
} from "lucide-react";
import { ProtectedRoute } from "@/components/curio/auth/ProtectedRoute";
import { CurioNav } from "@/components/curio/CurioNav";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { DocumentUploadZone } from "@/components/curio/documents/DocumentUploadZone";
import { DocumentCard } from "@/components/curio/documents/DocumentCard";
import { DocumentToolbar } from "@/components/curio/documents/DocumentToolbar";
import { DeleteDocumentDialog } from "@/components/curio/documents/DeleteDocumentDialog";
import { listDocuments } from "@/services/documentService";
import { startSession } from "@/services/sessionService";
import { useAuthStore } from "@/stores/authStore";
import { curioToast } from "@/components/curio/CurioToast";
import {
  DocumentItem,
  DocumentFilterStatus,
  DocumentSortOption,
} from "@/types/document";

export default function DocumentsPage() {
  return (
    <ProtectedRoute>
      <DocumentsLibraryContent />
    </ProtectedRoute>
  );
}

function DocumentsLibraryContent() {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter & sort state
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<DocumentFilterStatus>("ALL");
  const [sortBy, setSortBy] = useState<DocumentSortOption>("NEWEST");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  // Upload drawer / zone toggle
  const [showUploadZone, setShowUploadZone] = useState(false);

  // Deletion modal state
  const [documentToDelete, setDocumentToDelete] = useState<DocumentItem | null>(null);

  // Fetch document library
  const fetchLibrary = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    setError(null);
    try {
      const res = await listDocuments(1, 100);
      setDocuments(res.documents || []);
    } catch (err: any) {
      if (!isSilent) {
        setError(err.message || "Failed to load document library.");
      }
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLibrary();
  }, [fetchLibrary]);

  // Polling for documents actively processing
  useEffect(() => {
    const hasActiveProcessing = documents.some(
      (d) => d.status === "PROCESSING" || d.status === "UPLOADED"
    );
    if (!hasActiveProcessing) return;

    const timer = setInterval(() => {
      fetchLibrary(true);
    }, 4000);

    return () => clearInterval(timer);
  }, [documents, fetchLibrary]);

  // Document actions
  const handleUploadSuccess = (newDoc: DocumentItem) => {
    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.document_id !== newDoc.document_id)]);
    setShowUploadZone(false);
    fetchLibrary(true);
  };

  const handleStatusUpdated = (updatedDoc: DocumentItem) => {
    setDocuments((prev) =>
      prev.map((d) => (d.document_id === updatedDoc.document_id ? updatedDoc : d))
    );
  };

  const handleDocumentDeleted = (deletedId: string) => {
    setDocuments((prev) => prev.filter((d) => d.document_id !== deletedId));
  };

  const handleStartLearning = async (doc: DocumentItem) => {
    try {
      const res = await startSession(doc.filename, {
        sourceType: "DOCUMENT",
        documentId: doc.document_id,
      });
      curioToast.success(
        "GROUNDED SESSION STARTED",
        `Learning from '${doc.filename}'.`
      );
      router.push(`/session/${res.sessionId}?topic=${encodeURIComponent(doc.filename)}`);
    } catch (err: any) {
      curioToast.error(
        "COULD NOT START SESSION",
        err.message || "Please try again."
      );
    }
  };

  // Filter and sort computation
  const filteredDocuments = useMemo(() => {
    return documents
      .filter((doc) => {
        // Search filter
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          if (!doc.filename.toLowerCase().includes(q)) return false;
        }

        // Status filter
        if (statusFilter === "READY" && doc.status !== "PROCESSED") return false;
        if (
          statusFilter === "PROCESSING" &&
          doc.status !== "PROCESSING" &&
          doc.status !== "UPLOADED"
        )
          return false;
        if (statusFilter === "FAILED" && doc.status !== "FAILED") return false;

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "NEWEST") {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        }
        if (sortBy === "OLDEST") {
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        }
        if (sortBy === "NAME") {
          return a.filename.localeCompare(b.filename);
        }
        if (sortBy === "SIZE") {
          return b.file_size - a.file_size;
        }
        return 0;
      });
  }, [documents, searchQuery, statusFilter, sortBy]);

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white">
      <DiagonalSweepTransition />

      {/* Authenticated Global Navigation Bar */}
      <CurioNav activeRoute="documents" />

      {/* Main Document Library Stage */}
      <main className="max-w-6xl w-full mx-auto px-6 py-8 md:py-12 flex-1">
        {/* Page Hero Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-heading text-2xl md:text-3xl font-bold text-navy">
                My Documents
              </h1>
              {!loading && (
                <span className="font-mono text-xs font-bold px-2 py-0.5 bg-navy text-white rounded-[3px]">
                  {documents.length}
                </span>
              )}
            </div>
            <p className="font-sans text-sm text-navy/70 mt-1 max-w-xl">
              Upload textbook chapters, research papers, or study notes. Curio indexes the text into verified chunks and tests your comprehension using the Feynman technique.
            </p>
          </div>

          <KeycapButton
            variant="cobalt"
            size="md"
            onClick={() => setShowUploadZone((prev) => !prev)}
            className="shrink-0"
          >
            <Plus className="w-4 h-4 mr-1" />
            {showUploadZone ? "[HIDE UPLOAD]" : "[UPLOAD DOCUMENT]"}
          </KeycapButton>
        </div>

        {/* Collapsible Upload Zone */}
        {showUploadZone && (
          <div className="mb-8 animate-in fade-in slide-in-from-top-2 duration-150">
            <DocumentUploadZone onUploadSuccess={handleUploadSuccess} />
          </div>
        )}

        {/* Loading Skeletons */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="bg-white border-2 border-navy/20 rounded-[6px] p-5 h-48 animate-pulse space-y-3"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-fog/50 rounded-[4px]" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-4 bg-fog/50 rounded-[2px] w-3/4" />
                    <div className="h-3 bg-fog/30 rounded-[2px] w-1/3" />
                  </div>
                </div>
                <div className="h-5 bg-fog/30 rounded-[3px] w-28 mt-4" />
                <div className="grid grid-cols-2 gap-2 pt-4">
                  <div className="h-3 bg-fog/30 rounded-[2px]" />
                  <div className="h-3 bg-fog/30 rounded-[2px]" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="bg-white border-2 border-navy rounded-[6px] shadow-editorial p-8 text-center max-w-md mx-auto my-12">
            <AlertCircle className="w-10 h-10 text-rose-600 mx-auto mb-3" />
            <h3 className="font-heading text-lg font-bold text-navy mb-2">
              Could Not Load Documents
            </h3>
            <p className="font-mono text-xs text-navy/60 mb-6">
              {error}
            </p>
            <KeycapButton variant="navy" size="sm" onClick={() => fetchLibrary()}>
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
              [RETRY]
            </KeycapButton>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && documents.length === 0 && (
          <div className="bg-white border-2 border-navy rounded-[8px] shadow-[8px_8px_0_0_#0F2B4A] p-8 md:p-12 text-center max-w-xl mx-auto my-8">
            <div className="w-16 h-16 rounded-[6px] bg-ice border-2 border-navy flex items-center justify-center mx-auto mb-5 text-cobalt shadow-[3px_3px_0_0_#0F2B4A]">
              <FileText className="w-8 h-8" />
            </div>
            <h2 className="font-heading text-xl font-bold text-navy mb-2">
              No Learning Material Uploaded Yet
            </h2>
            <p className="font-sans text-sm text-navy/70 mb-6 max-w-md mx-auto leading-relaxed">
              Ground your Feynman sessions in your actual course materials. Upload a PDF, TXT, or DOCX document to get started.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <KeycapButton
                variant="cobalt"
                size="md"
                onClick={() => setShowUploadZone(true)}
              >
                <Upload className="w-4 h-4 mr-1.5" />
                [UPLOAD YOUR FIRST DOCUMENT]
              </KeycapButton>

              <Link href="/topics">
                <KeycapButton variant="ghost" size="md">
                  [GENERAL LEARNING →]
                </KeycapButton>
              </Link>
            </div>
          </div>
        )}

        {/* Populated Library View */}
        {!loading && !error && documents.length > 0 && (
          <>
            {/* Toolbar */}
            <DocumentToolbar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
              sortBy={sortBy}
              onSortChange={setSortBy}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              totalCount={documents.length}
              filteredCount={filteredDocuments.length}
            />

            {/* No matches for search */}
            {filteredDocuments.length === 0 ? (
              <div className="bg-white border-2 border-navy/40 rounded-[6px] p-8 text-center my-6">
                <p className="font-heading text-sm font-bold text-navy">
                  No documents match your filter
                </p>
                <p className="font-mono text-xs text-navy/50 mt-1 mb-4">
                  Try adjusting your search query or status filter.
                </p>
                <button
                  onClick={() => {
                    setSearchQuery("");
                    setStatusFilter("ALL");
                  }}
                  className="font-mono text-xs font-bold text-cobalt hover:underline uppercase"
                >
                  [Reset Filters]
                </button>
              </div>
            ) : viewMode === "grid" ? (
              /* Grid Layout */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredDocuments.map((doc) => (
                  <DocumentCard
                    key={doc.document_id}
                    document={doc}
                    onDeleteRequest={setDocumentToDelete}
                    onStatusUpdated={handleStatusUpdated}
                    onStartLearning={handleStartLearning}
                  />
                ))}
              </div>
            ) : (
              /* List Layout */
              <div className="space-y-3">
                {filteredDocuments.map((doc) => (
                  <DocumentCard
                    key={doc.document_id}
                    document={doc}
                    onDeleteRequest={setDocumentToDelete}
                    onStatusUpdated={handleStatusUpdated}
                    onStartLearning={handleStartLearning}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </main>

      {/* Delete Confirmation Dialog */}
      <DeleteDocumentDialog
        document={documentToDelete}
        isOpen={Boolean(documentToDelete)}
        onClose={() => setDocumentToDelete(null)}
        onDeleted={handleDocumentDeleted}
      />
    </div>
  );
}
