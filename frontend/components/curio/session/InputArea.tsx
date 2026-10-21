"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Plus,
  Mic,
  Square,
  Send,
  FileText,
  Upload,
  FolderOpen,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  ExternalLink,
  X,
} from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { SessionMode } from "@/types/session";
import { DocumentItem } from "@/types/document";
import { curioToast } from "@/components/curio/CurioToast";
import { useSessionStore } from "@/stores/sessionStore";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import {
  validateDocumentFile,
  uploadDocument,
  processDocument,
  getDocument,
} from "@/services/documentService";
import { DocumentPickerModal } from "@/components/curio/session/DocumentPickerModal";

export interface InputAreaProps {
  mode: SessionMode;
  onSendMessage: (content: string) => void | Promise<void>;
  onStuck: () => void;
  onFinishSession: () => void;
  onAttachmentClick?: () => void;
  disabled?: boolean;
  documentId?: string;
  onAttachDocument?: (documentId: string) => Promise<void>;
  onDetachDocument?: () => Promise<void>;
}

type UploadPhase = "idle" | "validating" | "uploading" | "processing" | "ready" | "failed";

export function InputArea({
  mode,
  onSendMessage,
  onStuck,
  onFinishSession,
  onAttachmentClick,
  disabled = false,
  documentId: propDocId,
  onAttachDocument,
  onDetachDocument,
}: InputAreaProps) {
  const store = useSessionStore();
  const effectiveDocId = propDocId !== undefined ? propDocId : store.documentId;
  const attachFn = onAttachDocument || store.attachDocument;
  const detachFn = onDetachDocument || store.detachDocument;

  const [content, setContent] = useState("");
  const [uploadPhase, setUploadPhase] = useState<UploadPhase>("idle");
  const [attachedDoc, setAttachedDoc] = useState<DocumentItem | null>(null);
  const [activeFileName, setActiveFileName] = useState<string>("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState<boolean>(false);
  const [attachMenuOpen, setAttachMenuOpen] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Audio recording and Whisper transcription lifecycle
  const {
    state: voiceState,
    duration: voiceDuration,
    error: voiceError,
    startRecording,
    stopRecording,
    cancelRecording,
    clearError: clearVoiceError,
    isRecording,
    isTranscribing,
    isRequestingPermission,
  } = useAudioRecorder({
    onTranscriptionSuccess: async (transcribedText) => {
      const clean = transcribedText.trim();
      if (!clean) return;
      curioToast.success(
        "VOICE SENT",
        `Sent: "${clean.length > 50 ? clean.slice(0, 50) + "..." : clean}"`
      );
      try {
        await onSendMessage(clean);
        setContent("");
        if (textareaRef.current) {
          textareaRef.current.style.height = "auto";
        }
      } catch (err: any) {
        console.error("Failed to automatically send voice message:", err);
      }
    },
    onError: (err) => {
      curioToast.error("VOICE ERROR", err.message || "Failed to record or transcribe audio.");
    },
  });

  const isTeacher = mode === "TEACHER";
  const placeholder = isTeacher
    ? "Ask Curio a question or explain your understanding..."
    : "Explain your reasoning to Curio...";

  // Hydrate document when effectiveDocId is present
  useEffect(() => {
    if (!effectiveDocId) {
      setAttachedDoc(null);
      setUploadPhase("idle");
      setActiveFileName("");
      return;
    }

    let isMounted = true;
    getDocument(effectiveDocId)
      .then((doc) => {
        if (isMounted) {
          setAttachedDoc(doc);
          setActiveFileName(doc.filename);
          if (doc.status === "PROCESSED") {
            setUploadPhase("ready");
          } else if (doc.status === "FAILED") {
            setUploadPhase("failed");
          } else {
            setUploadPhase("processing");
          }
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn("Could not load attached document:", err);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [effectiveDocId]);

  // Polling while document is in processing state
  useEffect(() => {
    if (uploadPhase !== "processing" || !attachedDoc?.document_id) return;

    const interval = setInterval(async () => {
      try {
        const latest = await getDocument(attachedDoc.document_id);
        if (latest.status === "PROCESSED") {
          setAttachedDoc(latest);
          setUploadPhase("ready");
          await attachFn(latest.document_id);
          curioToast.success(
            "DOCUMENT READY",
            `"${latest.filename}" is now grounding this conversation.`
          );
          clearInterval(interval);
        } else if (latest.status === "FAILED") {
          setAttachedDoc(latest);
          setUploadPhase("failed");
          setUploadError("Text extraction failed.");
          curioToast.error(
            "EXTRACTION FAILED",
            "Could not extract document text. You may retry processing."
          );
          clearInterval(interval);
        }
      } catch (err: any) {
        console.warn("Error polling document status:", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [uploadPhase, attachedDoc?.document_id, attachFn]);

  // Close attachment dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setAttachMenuOpen(false);
      }
    };
    if (attachMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [attachMenuOpen]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, [mode]);

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    setActiveFileName(file.name);
    setUploadPhase("validating");
    setUploadError(null);

    const validation = validateDocumentFile(file);
    if (!validation.valid) {
      setUploadPhase("failed");
      const errStr = validation.error || "Unsupported file format or size limit exceeded.";
      setUploadError(errStr);
      curioToast.error("VALIDATION ERROR", errStr);
      return;
    }

    try {
      setUploadPhase("uploading");
      const uploadedDoc = await uploadDocument(file);
      setAttachedDoc(uploadedDoc);

      setUploadPhase("processing");
      await processDocument(uploadedDoc.document_id);
    } catch (err: any) {
      setUploadPhase("failed");
      const msg = err?.message || "Document upload failed.";
      setUploadError(msg);
      curioToast.error("UPLOAD FAILED", msg);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
      e.target.value = "";
    }
  };

  const handleDetach = async () => {
    try {
      await detachFn();
      setAttachedDoc(null);
      setUploadPhase("idle");
      setActiveFileName("");
      setUploadError(null);
      curioToast.info(
        "DOCUMENT DETACHED",
        "Document unlinked from this conversation. The file remains in your library."
      );
    } catch (err: any) {
      console.warn("Failed to detach document:", err);
    }
  };

  const handleRetryProcessing = async () => {
    if (!attachedDoc?.document_id) return;
    try {
      setUploadPhase("processing");
      setUploadError(null);
      await processDocument(attachedDoc.document_id);
    } catch (err: any) {
      setUploadPhase("failed");
      setUploadError(err?.message || "Retry failed.");
    }
  };

  const handleSelectLibraryDoc = async (doc: DocumentItem) => {
    setAttachedDoc(doc);
    setActiveFileName(doc.filename);
    setUploadPhase("ready");
    setUploadError(null);
    await attachFn(doc.document_id);
    curioToast.success(
      "DOCUMENT ATTACHED",
      `"${doc.filename}" is now grounding this conversation.`
    );
  };

  const handleSend = async () => {
    if (!content.trim() || disabled) return;

    if (uploadPhase === "uploading" || uploadPhase === "processing") {
      curioToast.info(
        "PROCESSING DOCUMENT",
        "Please wait for your document to finish processing before sending."
      );
      return;
    }

    const msg = content.trim();
    try {
      await onSendMessage(msg);
      setContent("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    } catch (err) {
      // Draft preserved in content!
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const getExtension = (name: string) => {
    const parts = name.split(".");
    return parts.length > 1 ? parts.pop()?.toUpperCase() : "DOC";
  };

  const ext = getExtension(activeFileName || attachedDoc?.filename || "");
  const isBusyProcessing = uploadPhase === "uploading" || uploadPhase === "processing" || uploadPhase === "validating";

  return (
    <div className="w-full max-w-4xl mx-auto px-4 md:px-8 pb-6 pt-2">
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        id="chat-file-input"
        type="file"
        accept=".pdf,.txt,.docx"
        onChange={handleFileInputChange}
        className="hidden"
        aria-label="Upload document"
      />

      {/* Library Picker Modal */}
      <DocumentPickerModal
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelectDocument={handleSelectLibraryDoc}
        onUploadClick={() => fileInputRef.current?.click()}
        currentDocumentId={attachedDoc?.document_id}
      />

      {/* Composer Box Container with Drag & Drop */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`bg-white border-2 rounded-[8px] p-3 transition-all duration-150 relative ${
          isDragging
            ? "border-dashed border-cobalt bg-ice/40 shadow-[0_4px_0_0_#3A63FF]"
            : "border-navy shadow-[0_4px_0_0_#0F2B4A] focus-within:border-cobalt focus-within:shadow-[0_4px_0_0_#3A63FF]"
        }`}
      >
        {/* Drag Overlay Hint */}
        {isDragging && (
          <div className="absolute inset-0 bg-white/90 backdrop-blur-[1px] rounded-[6px] z-20 flex items-center justify-center pointer-events-none">
            <div className="flex items-center gap-2 text-cobalt font-mono font-bold text-xs uppercase tracking-wider">
              <Upload className="w-4 h-4 animate-bounce" />
              Drop document to attach (.pdf, .txt, .docx up to 10MB)
            </div>
          </div>
        )}

        {/* Active Voice Recording Status Bar */}
        {isRecording && (
          <div
            id="voice-recording-banner"
            className="flex items-center justify-between gap-3 px-3 py-2 mb-2 bg-rose-50/90 border border-rose-200 rounded-[6px] animate-in fade-in"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="relative flex h-2.5 w-2.5 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-600"></span>
              </span>
              <span className="font-mono text-xs font-bold text-rose-700 shrink-0">
                {Math.floor(voiceDuration / 60)}:{String(voiceDuration % 60).padStart(2, "0")}
              </span>
              <span className="text-xs text-rose-800 font-sans truncate hidden sm:inline">
                Recording question... Speak clearly
              </span>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                id="voice-cancel-btn"
                type="button"
                onClick={cancelRecording}
                className="px-2 py-1 text-xs font-mono font-medium text-rose-700 hover:text-rose-900 hover:bg-rose-100 rounded transition-colors"
                title="Discard audio recording"
              >
                Discard
              </button>
              <button
                id="voice-stop-btn"
                type="button"
                onClick={stopRecording}
                className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono font-semibold bg-rose-600 text-white hover:bg-rose-700 rounded shadow-sm transition-colors cursor-pointer"
                title="Finish recording and transcribe"
              >
                <Square className="w-3 h-3 fill-current" />
                <span>Done</span>
              </button>
            </div>
          </div>
        )}

        {/* Transcribing Indicator */}
        {isTranscribing && (
          <div
            id="voice-transcribing-banner"
            className="flex items-center gap-2 px-3 py-2 mb-2 bg-cobalt/10 border border-cobalt/20 rounded-[6px] text-xs font-mono text-cobalt animate-pulse"
          >
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Transcribing spoken audio with Whisper...</span>
          </div>
        )}

        {/* Voice Error Notice */}
        {voiceError && !isRecording && !isTranscribing && (
          <div
            id="voice-error-banner"
            className="flex items-center justify-between gap-2 px-3 py-1.5 mb-2 bg-rose-50 border border-rose-200 rounded-[6px] text-xs font-sans text-rose-700 animate-in fade-in"
          >
            <div className="flex items-center gap-1.5 min-w-0">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-600" />
              <span className="truncate">{voiceError}</span>
            </div>
            <button
              type="button"
              onClick={clearVoiceError}
              className="p-1 hover:bg-rose-100 rounded text-rose-700"
              title="Dismiss error"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Selected Document Indicator (Chip) */}
        {(attachedDoc || uploadPhase !== "idle") && (
          <div
            id="attached-doc-chip"
            className="flex items-center justify-between gap-2 px-2.5 py-1.5 mb-2.5 bg-slate-50 border border-slate-200 rounded-[6px] text-xs font-mono transition-all animate-in fade-in"
          >
            <div className="flex items-center gap-2 min-w-0">
              <div
                className={`w-6 h-6 rounded-[3px] flex items-center justify-center shrink-0 text-[9px] font-bold uppercase ${
                  ext === "PDF"
                    ? "bg-rose-100 text-rose-700"
                    : ext === "DOCX"
                    ? "bg-blue-100 text-blue-700"
                    : "bg-emerald-100 text-emerald-700"
                }`}
              >
                {ext}
              </div>

              <span
                className="font-sans font-medium text-navy truncate max-w-[160px] sm:max-w-xs md:max-w-md"
                title={activeFileName}
              >
                {activeFileName || "Document"}
              </span>

              {/* Honest status badges */}
              {uploadPhase === "validating" && (
                <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-[3px]">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                  Validating...
                </span>
              )}
              {uploadPhase === "uploading" && (
                <span className="inline-flex items-center gap-1 text-[10px] text-cyan-700 bg-cyan-50 border border-cyan-200 px-1.5 py-0.5 rounded-[3px]">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                  Uploading...
                </span>
              )}
              {uploadPhase === "processing" && (
                <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-300 px-1.5 py-0.5 rounded-[3px] animate-pulse">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                  Processing text...
                </span>
              )}
              {uploadPhase === "ready" && (
                <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-300 px-1.5 py-0.5 rounded-[3px]">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  Ready
                </span>
              )}
              {uploadPhase === "failed" && (
                <span className="inline-flex items-center gap-1 text-[10px] text-rose-700 bg-rose-50 border border-rose-300 px-1.5 py-0.5 rounded-[3px]">
                  <AlertCircle className="w-2.5 h-2.5" />
                  {uploadError || "Failed"}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {uploadPhase === "failed" && attachedDoc?.document_id && (
                <button
                  type="button"
                  onClick={handleRetryProcessing}
                  className="p-1 text-rose-600 hover:text-rose-800 hover:bg-rose-100 rounded text-[11px] font-sans flex items-center gap-0.5"
                  title="Retry text extraction"
                >
                  <RefreshCw className="w-3 h-3" />
                  Retry
                </button>
              )}

              {attachedDoc?.document_id && (
                <Link
                  href={`/documents/${attachedDoc.document_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1 text-slate-400 hover:text-cobalt rounded"
                  title="View document details in new tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              )}

              <button
                id="doc-detach-btn"
                type="button"
                onClick={handleDetach}
                className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50 transition-colors"
                title="Detach document from this session (does not delete file from library)"
                aria-label="Detach document"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        <div className="flex items-end gap-2.5">
          {/* Attachment Button with Popover Menu */}
          <div className="relative shrink-0 mb-0.5" ref={menuRef}>
            <button
              id="chat-attach-btn"
              type="button"
              onClick={() => setAttachMenuOpen((prev) => !prev)}
              className={`p-2 rounded-[4px] transition-colors ${
                attachedDoc
                  ? "text-cobalt bg-ice/60 hover:bg-ice"
                  : "text-navy/40 hover:text-cobalt hover:bg-ice"
              }`}
              title="Attach grounding document (PDF, TXT, DOCX)"
              aria-label="Attach document options"
            >
              <Plus className="w-4 h-4" />
            </button>

            {/* Attachment Dropdown Menu */}
            {attachMenuOpen && (
              <div className="absolute bottom-full left-0 mb-2 w-56 bg-white border-2 border-navy rounded-[6px] shadow-[0_4px_0_0_#0F2B4A] p-1.5 z-30 animate-in fade-in slide-in-from-bottom-1 font-sans text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setAttachMenuOpen(false);
                    fileInputRef.current?.click();
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-2 text-left rounded-[4px] hover:bg-ice text-navy hover:text-cobalt font-medium transition-colors"
                >
                  <Upload className="w-3.5 h-3.5 text-cobalt" />
                  <span>Upload from device</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setAttachMenuOpen(false);
                    setPickerOpen(true);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-2 text-left rounded-[4px] hover:bg-ice text-navy hover:text-cobalt font-medium transition-colors"
                >
                  <FolderOpen className="w-3.5 h-3.5 text-navy/60" />
                  <span>Select from library</span>
                </button>

                {attachedDoc && (
                  <>
                    <div className="border-t border-slate-100 my-1" />
                    <button
                      type="button"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        handleDetach();
                      }}
                      className="w-full flex items-center gap-2 px-2.5 py-2 text-left rounded-[4px] hover:bg-rose-50 text-rose-700 font-medium transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Detach document</span>
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Main Textarea */}
          <textarea
            ref={textareaRef}
            rows={2}
            value={content}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="flex-1 resize-none bg-transparent font-sans text-sm md:text-base text-navy placeholder:text-navy/40 focus:outline-none min-h-[48px] max-h-[180px] py-1 leading-relaxed"
          />

          {/* Microphone recording button */}
          <button
            id="voice-record-btn"
            type="button"
            onClick={() => {
              if (isRecording) {
                stopRecording();
              } else if (!isTranscribing && !isRequestingPermission && !disabled) {
                startRecording();
              }
            }}
            disabled={disabled || isTranscribing || isRequestingPermission}
            className={`h-[42px] w-[42px] rounded-[4px] inline-flex items-center justify-center transition-all shrink-0 cursor-pointer ${
              isRecording
                ? "bg-rose-600 text-white border-2 border-rose-700 animate-pulse shadow-[0_0_12px_rgba(225,29,72,0.4)]"
                : isTranscribing
                ? "bg-cobalt/15 text-cobalt border-2 border-cobalt/40"
                : isRequestingPermission
                ? "bg-amber-100 text-amber-800 border-2 border-amber-300"
                : "bg-white text-navy/70 border-2 border-navy/20 hover:text-cobalt hover:border-cobalt hover:bg-cobalt/5 shadow-[0_2px_0_0_#0F2B4A] active:translate-y-[2px] active:shadow-none"
            }`}
            title={
              isRecording
                ? "Click to finish recording and transcribe"
                : isTranscribing
                ? "Transcribing audio..."
                : isRequestingPermission
                ? "Requesting microphone permission..."
                : "Record question with microphone (Whisper)"
            }
            aria-label={isRecording ? "Stop recording voice" : "Start recording voice"}
          >
            {isTranscribing || isRequestingPermission ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isRecording ? (
              <Square className="w-5 h-5 fill-current" />
            ) : (
              <Mic className="w-5 h-5" />
            )}
          </button>

          {/* Send Button */}
          <KeycapButton
            id="chat-send-btn"
            onClick={handleSend}
            disabled={!content.trim() || disabled || isBusyProcessing}
            variant="navy"
            size="md"
            className="shrink-0"
            title={isBusyProcessing ? "Waiting for document processing to finish..." : undefined}
          >
            <span className="hidden sm:inline">
              {isBusyProcessing ? "PROCESSING..." : isTeacher ? "SUBMIT" : "EXPLAIN"}
            </span>
            <Send className="w-3.5 h-3.5 sm:ml-1" />
          </KeycapButton>
        </div>

        {/* Composer Footer Hints */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-fog/50 px-1 text-[11px] font-mono text-navy/50">
          <span>
            Press <kbd className="font-semibold text-navy bg-ice px-1 py-0.5 rounded-[2px]">Enter ↵</kbd> to send, <kbd className="font-semibold text-navy bg-ice px-1 py-0.5 rounded-[2px]">Shift+Enter</kbd> for newline
          </span>
          <span className="hidden sm:inline">
            {content.length > 0 ? `${content.length} chars` : ""}
          </span>
        </div>
      </div>

      {/* Sub-actions */}
      <div className="flex items-center justify-between mt-3 px-1">
        <KeycapButton
          onClick={onFinishSession}
          variant="ghost"
          size="sm"
          className="text-navy/80 hover:text-white text-xs"
        >
          [FINISH SESSION]
        </KeycapButton>

        <KeycapButton
          onClick={onStuck}
          disabled={isTeacher || disabled}
          variant={isTeacher ? "ghost" : "gap"}
          size="sm"
          title={isTeacher ? "Currently addressing identified gap" : "Ask Curio to teach this specific concept"}
          className="text-xs"
        >
          {isTeacher ? "[ADDRESSING GAP]" : "[I'M STUCK]"}
        </KeycapButton>
      </div>
    </div>
  );
}
