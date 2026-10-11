"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  File,
  Layers,
  HardDrive,
  Calendar,
  ExternalLink,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  FolderOpen,
  Info,
  X,
} from "lucide-react";
import { DocumentItem } from "@/types/document";
import { getDocument, formatFileSize, formatDocumentStatus } from "@/services/documentService";

export interface DocumentContextPanelProps {
  documentId?: string;
  isOpen: boolean;
  onToggle: () => void;
  onDeselect?: () => void;
}

export function DocumentContextPanel({
  documentId,
  isOpen,
  onToggle,
  onDeselect,
}: DocumentContextPanelProps) {
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      setDocument(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    getDocument(documentId)
      .then((data) => {
        if (isMounted) setDocument(data);
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || "Could not load document context");
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [documentId]);

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed md:static right-0 top-20 z-20 flex items-center gap-1.5 px-3 py-2 bg-white border-l border-y md:border border-slate-200/90 text-navy hover:text-cobalt shadow-sm rounded-l-lg md:rounded-lg text-xs font-mono font-medium transition-colors"
        title="Show Document Context"
      >
        <FileText className="w-3.5 h-3.5 text-cobalt" />
        <span className="hidden lg:inline">
          {document ? document.filename : "Document Context"}
        </span>
        <ChevronLeft className="w-3 h-3 text-slate-400" />
      </button>
    );
  }

  const getExtension = (name: string) => {
    const parts = name.split(".");
    return parts.length > 1 ? parts.pop()?.toUpperCase() : "DOC";
  };

  return (
    <aside
      className="fixed md:static inset-y-0 right-0 z-40 w-80 md:w-80 bg-white border-l border-slate-200 flex flex-col shadow-lg md:shadow-none transition-all duration-300 font-sans"
      aria-label="Document Grounding Context"
    >
      {/* Panel Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cobalt" />
          <span className="text-xs font-mono uppercase tracking-wider font-bold text-navy">
            Grounding Context
          </span>
        </div>
        <button
          onClick={onToggle}
          className="p-1 text-slate-400 hover:text-navy rounded hover:bg-slate-50 transition-colors"
          title="Collapse context panel (does not unlink or delete document)"
          aria-label="Collapse panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {loading && (
          <div className="space-y-4 animate-pulse">
            <div className="h-16 bg-slate-100 rounded-xl" />
            <div className="h-24 bg-slate-100 rounded-xl" />
            <div className="h-32 bg-slate-100 rounded-xl" />
          </div>
        )}

        {!loading && error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              Document Not Available
            </div>
            <p className="text-rose-700 leading-relaxed">
              {error.includes("404")
                ? "This document may have been deleted or moved."
                : error}
            </p>
            <Link
              href="/documents"
              className="inline-flex items-center gap-1.5 font-mono text-[11px] text-rose-900 underline font-semibold mt-1"
            >
              Open Document Library →
            </Link>
          </div>
        )}

        {!loading && !error && document && (
          <>
            {/* Document Card */}
            {(() => {
              const statusInfo = formatDocumentStatus(document.status);
              const ext = getExtension(document.filename);

              return (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-cobalt/10 border border-cobalt/20 flex flex-col items-center justify-center text-cobalt shrink-0">
                      {ext === "PDF" ? (
                        <FileText className="w-4 h-4" />
                      ) : (
                        <File className="w-4 h-4" />
                      )}
                      <span className="text-[9px] font-mono font-bold uppercase">
                        {ext}
                      </span>
                    </div>

                    <div className="min-w-0 flex-1">
                      <h3
                        className="text-xs font-bold font-sora text-navy truncate"
                        title={document.filename}
                      >
                        {document.filename}
                      </h3>
                      <div className="mt-1">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium border ${statusInfo.badgeClass}`}
                        >
                          {statusInfo.isReady && (
                            <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />
                          )}
                          {statusInfo.isProcessing && (
                            <RefreshCw className="w-2.5 h-2.5 text-amber-600 animate-spin" />
                          )}
                          {statusInfo.isFailed && (
                            <AlertCircle className="w-2.5 h-2.5 text-rose-600" />
                          )}
                          {statusInfo.label}
                        </span>
                      </div>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-500 leading-relaxed font-sans">
                    {statusInfo.description}
                  </p>
                </div>
              );
            })()}

            {/* Real Metadata */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold block px-1">
                Grounded Knowledge Specs
              </span>
              <div className="rounded-xl border border-slate-200/80 bg-white divide-y divide-slate-100 text-xs font-mono">
                <div className="flex items-center justify-between p-2.5">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    Indexed Chunks
                  </span>
                  <span className="font-bold text-navy">{document.chunk_count}</span>
                </div>

                <div className="flex items-center justify-between p-2.5">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                    File Size
                  </span>
                  <span className="text-navy font-semibold">
                    {formatFileSize(document.file_size)}
                  </span>
                </div>

                {document.page_count !== null && document.page_count !== undefined && (
                  <div className="flex items-center justify-between p-2.5">
                    <span className="text-slate-500">Pages</span>
                    <span className="text-navy">{document.page_count}</span>
                  </div>
                )}

                <div className="flex items-center justify-between p-2.5">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    Uploaded
                  </span>
                  <span className="text-slate-700 text-[11px]">
                    {new Date(document.created_at).toLocaleDateString([], {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </div>
              </div>
            </div>

            {/* Educational grounding callout */}
            <div className="p-3.5 rounded-xl bg-cobalt/5 border border-cobalt/15 space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-mono uppercase font-bold text-cobalt">
                <Info className="w-3.5 h-3.5" />
                Active Feynman Context
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed font-sans">
                Curio uses the chunks in this document to challenge your explanations and verify technical assertions against the source text.
              </p>
            </div>

            {/* Document Action Links */}
            <div className="space-y-2 pt-2">
              <Link
                href={`/documents/${document.document_id}`}
                className="w-full inline-flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-cobalt text-xs font-mono text-navy hover:text-cobalt bg-white hover:bg-slate-50 transition-colors group"
              >
                <span>Full Document Details</span>
                <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-cobalt" />
              </Link>

              <Link
                href="/documents"
                className="w-full inline-flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-slate-300 text-xs font-mono text-slate-600 hover:text-navy bg-white hover:bg-slate-50 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <FolderOpen className="w-3.5 h-3.5 text-slate-400" />
                  My Documents Library
                </span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </Link>

              {onDeselect && (
                <button
                  type="button"
                  onClick={onDeselect}
                  className="w-full inline-flex items-center justify-between p-2.5 rounded-lg border border-rose-200 hover:border-rose-300 text-xs font-mono text-rose-700 bg-rose-50/50 hover:bg-rose-50 transition-colors"
                >
                  <span className="flex items-center gap-1.5">
                    <X className="w-3.5 h-3.5 text-rose-500" />
                    Detach from Session
                  </span>
                  <span className="text-[10px] text-rose-400 font-sans">Keep in library</span>
                </button>
              )}
            </div>

          </>
        )}

        {!loading && !document && !documentId && (
          <div className="p-6 text-center space-y-3">
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
              <FileText className="w-5 h-5" />
            </div>
            <h4 className="text-xs font-bold font-sora text-navy">
              No Document Linked
            </h4>
            <p className="text-[11px] text-slate-500 leading-relaxed font-sans">
              This session is running in General Concept Mode. To anchor your learning in textbook chapters or papers, start a session from your documents.
            </p>
            <Link
              href="/documents"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-navy text-white text-xs font-mono uppercase font-semibold hover:bg-navy/90 transition-colors mt-2"
            >
              Browse Library →
            </Link>
          </div>
        )}
      </div>

      {/* Footer Notice: Deselect vs Delete clarity */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/60 text-[10px] font-mono text-slate-400 text-center shrink-0">
        Closing or hiding this panel does not delete the document from your library.
      </div>
    </aside>
  );
}
