"use client";

import React, { useState } from "react";
import { AlertTriangle, Trash2, X } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { deleteDocument } from "@/services/documentService";
import { curioToast } from "@/components/curio/CurioToast";
import { DocumentItem } from "@/types/document";

export interface DeleteDocumentDialogProps {
  document: DocumentItem | null;
  isOpen: boolean;
  onClose: () => void;
  onDeleted: (documentId: string) => void;
}

export function DeleteDocumentDialog({
  document,
  isOpen,
  onClose,
  onDeleted,
}: DeleteDocumentDialogProps) {
  const [deleting, setDeleting] = useState(false);

  if (!isOpen || !document) return null;

  const handleDelete = async () => {
    if (deleting) return;
    setDeleting(true);

    try {
      await deleteDocument(document.document_id);
      curioToast.success(
        "DOCUMENT DELETED",
        `'${document.filename}' was removed from your library.`
      );
      onDeleted(document.document_id);
      onClose();
    } catch (err: any) {
      const message = err.message || "Failed to delete document. Please try again.";
      curioToast.error("DELETION FAILED", message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 backdrop-blur-[2px] p-4 animate-in fade-in duration-150"
    >
      <div className="w-full max-w-md bg-white border-2 border-navy rounded-[4px] shadow-[8px_8px_0_0_#0F2B4A] p-6 text-navy relative">
        <button
          onClick={onClose}
          disabled={deleting}
          className="absolute top-4 right-4 text-navy/40 hover:text-navy disabled:opacity-50 transition-colors p-1"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-start gap-3.5 mb-4">
          <div className="w-10 h-10 rounded-[4px] bg-rose-50 border border-rose-200 flex items-center justify-center shrink-0 text-rose-600">
            <Trash2 className="w-5 h-5" />
          </div>
          <div>
            <h3 id="delete-dialog-title" className="font-heading text-lg font-bold text-navy">
              Delete Document?
            </h3>
            <p className="font-mono text-xs text-navy/50 mt-0.5 break-all">
              {document.filename}
            </p>
          </div>
        </div>

        <p className="font-sans text-sm text-navy/80 mb-6 leading-relaxed">
          This will permanently delete the document from your library and purge its extracted text chunks. Learning sessions that previously referenced this document will preserve their conversation history, but document grounding will no longer be available.
        </p>

        <div className="flex items-center justify-end gap-3 pt-2 border-t border-fog/60">
          <KeycapButton
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={deleting}
          >
            [CANCEL]
          </KeycapButton>
          <KeycapButton
            variant="gap"
            size="sm"
            onClick={handleDelete}
            loading={deleting}
            loadingText="DELETING..."
          >
            [DELETE PERMANENTLY]
          </KeycapButton>
        </div>
      </div>
    </div>
  );
}
