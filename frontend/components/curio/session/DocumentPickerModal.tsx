"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  X,
  Search,
  Check,
  Upload,
  Loader2,
  FolderOpen,
  AlertCircle,
  Clock,
} from "lucide-react";
import { DocumentItem } from "@/types/document";
import {
  listDocuments,
  formatFileSize,
  formatDocumentStatus,
} from "@/services/documentService";
import { KeycapButton } from "@/components/curio/KeycapButton";

export interface DocumentPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDocument: (doc: DocumentItem) => void;
  onUploadClick: () => void;
  currentDocumentId?: string;
}

export function DocumentPickerModal({
  isOpen,
  onClose,
  onSelectDocument,
  onUploadClick,
  currentDocumentId,
}: DocumentPickerModalProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    listDocuments(1, 50)
      .then((res) => {
        if (isMounted) {
          setDocuments(res.documents || []);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || "Failed to load documents");
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase().trim())
  );

  const getExtension = (name: string) => {
    const parts = name.split(".");
    return parts.length > 1 ? parts.pop()?.toUpperCase() : "DOC";
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy/60 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Select Document from Library"
    >
      <div
        className="w-full max-w-xl bg-white border-2 border-navy rounded-[8px] shadow-[0_8px_0_0_#0F2B4A] flex flex-col max-h-[85vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-fog bg-slate-50">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-cobalt" />
            <h3 className="font-heading font-bold text-navy text-sm md:text-base">
              Select Document from Library
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-navy/40 hover:text-navy rounded hover:bg-slate-200 transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search & Actions Bar */}
        <div className="p-3 border-b border-fog/60 bg-white flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-navy/40" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search library documents..."
              className="w-full pl-8 pr-3 py-1.5 text-xs font-sans text-navy bg-slate-50 border border-slate-200 rounded-[4px] focus:outline-none focus:border-cobalt"
            />
          </div>
          <KeycapButton
            variant="ghost"
            size="sm"
            onClick={() => {
              onClose();
              onUploadClick();
            }}
            className="text-xs text-cobalt shrink-0"
          >
            <Upload className="w-3.5 h-3.5 mr-1" />
            Upload New
          </KeycapButton>
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-cobalt" />
              <span className="text-xs font-mono">Loading library documents...</span>
            </div>
          )}

          {!loading && error && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-[6px] text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && filteredDocs.length === 0 && (
            <div className="text-center py-10 space-y-2">
              <FileText className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs text-slate-500 font-sans">
                {searchQuery
                  ? "No documents match your search query."
                  : "No documents found in your library."}
              </p>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onUploadClick();
                }}
                className="text-xs text-cobalt font-semibold hover:underline inline-flex items-center gap-1"
              >
                <Upload className="w-3 h-3" />
                Upload a document now
              </button>
            </div>
          )}

          {!loading &&
            !error &&
            filteredDocs.map((doc) => {
              const statusInfo = formatDocumentStatus(doc.status);
              const isSelected = doc.document_id === currentDocumentId;
              const isReady = statusInfo.isReady;
              const ext = getExtension(doc.filename);

              return (
                <div
                  key={doc.document_id}
                  onClick={() => {
                    if (isReady) {
                      onSelectDocument(doc);
                      onClose();
                    }
                  }}
                  className={`p-3 rounded-[6px] border transition-all flex items-center justify-between gap-3 ${
                    isSelected
                      ? "bg-cobalt/5 border-cobalt shadow-sm"
                      : isReady
                      ? "bg-white hover:bg-slate-50 border-slate-200 hover:border-slate-300 cursor-pointer"
                      : "bg-slate-50/50 border-slate-200/60 opacity-60 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-8 h-8 rounded-[4px] flex items-center justify-center shrink-0 text-[10px] font-mono font-bold uppercase ${
                        ext === "PDF"
                          ? "bg-rose-100 text-rose-700"
                          : ext === "DOCX"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-emerald-100 text-emerald-700"
                      }`}
                    >
                      {ext}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-navy truncate font-sans">
                        {doc.filename}
                      </p>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400 mt-0.5">
                        <span>{formatFileSize(doc.file_size)}</span>
                        {doc.chunk_count > 0 && <span>· {doc.chunk_count} chunks</span>}
                        {doc.page_count && <span>· {doc.page_count} pages</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`px-2 py-0.5 rounded-[3px] text-[10px] font-mono border ${statusInfo.badgeClass}`}
                    >
                      {statusInfo.label}
                    </span>

                    {isSelected && (
                      <span className="p-1 rounded-full bg-cobalt text-white" title="Currently Attached">
                        <Check className="w-3 h-3" />
                      </span>
                    )}

                    {!isSelected && isReady && (
                      <span className="text-[11px] font-mono text-cobalt font-semibold hover:underline">
                        Select
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-fog bg-slate-50 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Supported: PDF, TXT, DOCX (up to 10MB)</span>
          <button
            type="button"
            onClick={onClose}
            className="text-navy hover:text-cobalt font-semibold"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
