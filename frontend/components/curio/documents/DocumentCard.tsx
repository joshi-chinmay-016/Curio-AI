"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  FileCode,
  File,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Play,
  RotateCcw,
  Trash2,
  ChevronRight,
  MoreVertical,
  ExternalLink,
  BookOpen,
} from "lucide-react";
import { DocumentItem } from "@/types/document";
import {
  formatFileSize,
  formatDocumentStatus,
  processDocument,
} from "@/services/documentService";
import { curioToast } from "@/components/curio/CurioToast";

export interface DocumentCardProps {
  document: DocumentItem;
  onDeleteRequest: (doc: DocumentItem) => void;
  onStatusUpdated?: (doc: DocumentItem) => void;
  onStartLearning?: (doc: DocumentItem) => void;
}

export function DocumentCard({
  document,
  onDeleteRequest,
  onStatusUpdated,
  onStartLearning,
}: DocumentCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [processing, setProcessing] = useState(false);

  const statusInfo = formatDocumentStatus(document.status);

  // File extension styling
  const ext = (document.filename.split(".").pop() || "").toLowerCase();
  const getFileIcon = () => {
    switch (ext) {
      case "pdf":
        return <FileText className="w-5 h-5 text-red-500" />;
      case "docx":
        return <File className="w-5 h-5 text-blue-600" />;
      case "txt":
        return <FileCode className="w-5 h-5 text-slate-600" />;
      default:
        return <FileText className="w-5 h-5 text-cobalt" />;
    }
  };

  const handleProcess = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (processing) return;
    setProcessing(true);
    setMenuOpen(false);

    try {
      const updated = await processDocument(document.document_id);
      curioToast.success("PROCESSING COMPLETE", `Text extracted from '${document.filename}'.`);
      onStatusUpdated?.(updated);
    } catch (err: any) {
      curioToast.error("PROCESSING ERROR", err.message || "Failed to process text.");
    } finally {
      setProcessing(false);
    }
  };

  const formattedDate = document.created_at
    ? new Date(document.created_at).toLocaleDateString([], {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Unknown date";

  return (
    <div className="bg-white dark:bg-[#0E1A2B] border-2 border-navy dark:border-[#2F4D73] rounded-[6px] shadow-editorial dark:shadow-[4px_4px_0_0_#040910] hover:shadow-editorial-lg hover:-translate-y-0.5 transition-all duration-150 flex flex-col justify-between relative group overflow-hidden">
      {/* Top Banner & Menu */}
      <div className="p-4 sm:p-5 pb-3">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-[4px] bg-ice dark:bg-[#16273F] border border-fog/80 dark:border-[#2F4D73] flex items-center justify-center shrink-0">
              {getFileIcon()}
            </div>
            <div className="min-w-0">
              <Link
                href={`/documents/${document.document_id}`}
                className="font-heading text-sm font-bold text-navy dark:text-[#F0F4F8] hover:text-cobalt dark:hover:text-[#4D7CFF] transition-colors truncate block"
                title={document.filename}
              >
                {document.filename}
              </Link>
              <span className="font-mono text-[11px] text-navy/50 dark:text-[#829AB1] uppercase tracking-wider block">
                {ext.toUpperCase()} • {formatFileSize(document.file_size)}
              </span>
            </div>
          </div>

          {/* Context Menu Toggle */}
          <div className="relative shrink-0">
            <button
              onClick={() => setMenuOpen((prev) => !prev)}
              className="p-1 text-navy/40 dark:text-[#829AB1] hover:text-navy dark:hover:text-white rounded-[3px] hover:bg-ice dark:hover:bg-[#1A3254] transition-colors cursor-pointer"
              aria-label="Document options"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {menuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setMenuOpen(false)}
                />
                <div className="absolute right-0 top-full mt-1 w-48 bg-white dark:bg-[#0B1524] border-2 border-navy dark:border-[#2F4D73] rounded-[4px] shadow-[4px_4px_0_0_#0F2B4A] dark:shadow-[4px_4px_0_0_#040910] z-50 py-1 font-mono text-xs">
                  <Link
                    href={`/documents/${document.document_id}`}
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-navy/80 dark:text-[#C5D0DE] hover:bg-ice dark:hover:bg-[#1A3254] hover:text-navy dark:hover:text-white transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>View Details</span>
                  </Link>

                  {(!statusInfo.isReady || statusInfo.isFailed) && (
                    <button
                      onClick={handleProcess}
                      disabled={processing}
                      className="w-full flex items-center gap-2 px-3 py-2 text-navy/80 dark:text-[#C5D0DE] hover:bg-ice dark:hover:bg-[#1A3254] hover:text-navy dark:hover:text-white transition-colors text-left cursor-pointer"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>{processing ? "Processing..." : "Process Text"}</span>
                    </button>
                  )}

                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onDeleteRequest(document);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors text-left border-t border-fog/40 dark:border-[#1E3652] cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Document</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2 mb-3">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[3px] font-mono text-[11px] font-semibold border ${statusInfo.badgeClass}`}
          >
            {statusInfo.isReady && <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />}
            {statusInfo.isProcessing && <Clock className="w-3 h-3 animate-spin text-amber-600 dark:text-amber-400" />}
            {statusInfo.isFailed && <AlertTriangle className="w-3 h-3 text-rose-600 dark:text-rose-400" />}
            <span>{statusInfo.label}</span>
          </span>
        </div>

        {/* Metadata Details */}
        <div className="grid grid-cols-2 gap-2 text-navy/70 dark:text-[#BAC7D5] text-xs font-mono pt-2 border-t border-fog/40 dark:border-[#1E3652]">
          <div>
            <span className="text-navy/40 dark:text-[#829AB1] text-[10px] block uppercase">PAGES</span>
            <span className="font-semibold text-navy dark:text-[#F0F4F8]">
              {document.page_count !== null && document.page_count !== undefined
                ? document.page_count
                : "—"}
            </span>
          </div>
          <div>
            <span className="text-navy/40 dark:text-[#829AB1] text-[10px] block uppercase">INDEXED CHUNKS</span>
            <span className="font-semibold text-navy dark:text-[#F0F4F8]">
              {document.chunk_count > 0 ? document.chunk_count : "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Card Action Footer */}
      <div className="px-4 sm:px-5 py-3 bg-ice/50 dark:bg-[#101F33] border-t border-fog/60 dark:border-[#1E3652] flex items-center justify-between text-xs font-mono">
        <span className="text-navy/40 dark:text-[#829AB1] text-[10px]">{formattedDate}</span>

        {statusInfo.isReady ? (
          <button
            onClick={() => onStartLearning?.(document)}
            className="inline-flex items-center gap-1.5 font-bold text-cobalt dark:text-[#4D7CFF] hover:text-navy dark:hover:text-white transition-colors cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>LEARN →</span>
          </button>
        ) : (
          <Link
            href={`/documents/${document.document_id}`}
            className="inline-flex items-center gap-1 text-navy/60 dark:text-[#BAC7D5] hover:text-navy dark:hover:text-white transition-colors"
          >
            <span>INSPECT</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>
    </div>
  );
}
