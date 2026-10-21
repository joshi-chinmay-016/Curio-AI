"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import {
  uploadDocument,
  processDocument,
  validateDocumentFile,
  formatFileSize,
  ALLOWED_EXTENSIONS,
} from "@/services/documentService";
import { curioToast } from "@/components/curio/CurioToast";
import { DocumentItem } from "@/types/document";

export interface DocumentUploadZoneProps {
  onUploadSuccess: (document: DocumentItem) => void;
  className?: string;
}

export function DocumentUploadZone({
  onUploadSuccess,
  className = "",
}: DocumentUploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleFileSelection = (file: File) => {
    setValidationError(null);
    const validation = validateDocumentFile(file);
    if (!validation.valid) {
      setValidationError(validation.error || "Invalid file");
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || uploading) return;

    setUploading(true);
    setValidationError(null);

    try {
      // 1. Upload document to storage
      const uploadedDoc = await uploadDocument(selectedFile);

      // 2. Automatically trigger extraction pipeline
      let finalDoc = uploadedDoc;
      try {
        finalDoc = await processDocument(uploadedDoc.document_id);
      } catch (procErr: any) {
        console.warn("Auto-process trigger error:", procErr);
      }

      curioToast.success(
        "UPLOAD SUCCESSFUL",
        `'${uploadedDoc.filename}' is uploaded and indexed.`
      );

      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      onUploadSuccess(finalDoc);
    } catch (err: any) {
      const msg = err.message || "Failed to upload document. Please check your connection.";
      setValidationError(msg);
      curioToast.error("UPLOAD FAILED", msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={`bg-white border-2 border-navy rounded-[6px] shadow-editorial p-6 ${className}`}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ALLOWED_EXTENSIONS.join(",")}
        className="hidden"
        onChange={handleInputChange}
        disabled={uploading}
      />

      {/* Drag & Drop Target */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-[4px] p-6 md:p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-150 ${
          isDragOver
            ? "border-cobalt bg-cobalt/5 scale-[0.99]"
            : selectedFile
            ? "border-emerald-500 bg-emerald-50/20"
            : "border-fog hover:border-navy/60 hover:bg-ice/40"
        }`}
      >
        <div className="w-12 h-12 rounded-[6px] bg-ice border border-fog flex items-center justify-center text-navy/70 mb-3 group-hover:text-cobalt transition-colors">
          {uploading ? (
            <Loader2 className="w-6 h-6 animate-spin text-cobalt" />
          ) : selectedFile ? (
            <FileText className="w-6 h-6 text-emerald-600" />
          ) : (
            <UploadCloud className="w-6 h-6 text-navy/70" />
          )}
        </div>

        {selectedFile ? (
          <div className="space-y-1">
            <p className="font-heading text-sm font-bold text-navy truncate max-w-md">
              {selectedFile.name}
            </p>
            <p className="font-mono text-xs text-navy/60">
              {formatFileSize(selectedFile.size)} • Click to choose a different file
            </p>
          </div>
        ) : (
          <div className="space-y-1.5">
            <p className="font-heading text-sm font-bold text-navy">
              Drag & drop your study material here, or{" "}
              <span className="text-cobalt underline decoration-cobalt/40 underline-offset-2">
                browse files
              </span>
            </p>
            <p className="font-mono text-xs text-navy/50">
              Supported formats: PDF, TXT, DOCX • Up to 100 MB per document
            </p>
          </div>
        )}
      </div>

      {/* Validation Error Message */}
      {validationError && (
        <div className="mt-3.5 p-3 bg-rose-50 border border-rose-200 rounded-[4px] flex items-center gap-2.5 text-rose-800 text-xs font-mono">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Action Footer if a file is staged */}
      {selectedFile && (
        <div className="mt-4 pt-3.5 border-t border-fog/60 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedFile(null);
              setValidationError(null);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
            disabled={uploading}
            className="text-xs font-mono uppercase font-bold text-navy/50 hover:text-navy disabled:opacity-40 transition-colors cursor-pointer"
          >
            [CANCEL SELECTION]
          </button>

          <KeycapButton
            variant="cobalt"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleUpload();
            }}
            loading={uploading}
            loadingText="INDEXING..."
          >
            [UPLOAD & INDEX DOCUMENT →]
          </KeycapButton>
        </div>
      )}
    </div>
  );
}
