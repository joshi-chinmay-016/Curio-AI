import { apiClient } from "@/services/apiClient";
import { DocumentItem, DocumentListResponse } from "@/types/document";

export const MAX_UPLOAD_SIZE = 10 * 1024 * 1024; // 10 MB in bytes
export const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".docx"];
export const ALLOWED_MIME_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export interface FileValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Validates a file against backend size and extension constraints before uploading.
 */
export function validateDocumentFile(file: File): FileValidationResult {
  if (!file) {
    return { valid: false, error: "No file selected." };
  }

  if (file.size === 0) {
    return { valid: false, error: "File is empty (0 bytes)." };
  }

  if (file.size > MAX_UPLOAD_SIZE) {
    return {
      valid: false,
      error: `File exceeds maximum allowed size of 10 MB (${(file.size / (1024 * 1024)).toFixed(1)} MB).`,
    };
  }

  const filename = file.name || "";
  const lastDot = filename.lastIndexOf(".");
  if (lastDot === -1) {
    return {
      valid: false,
      error: `File must have an extension. Allowed extensions: ${ALLOWED_EXTENSIONS.join(", ")}`,
    };
  }

  const extension = filename.substring(lastDot).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return {
      valid: false,
      error: `Unsupported file type '${extension}'. Supported formats: PDF, TXT, DOCX`,
    };
  }

  return { valid: true };
}

/**
 * Format bytes into human-readable size string.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Maps raw backend status to human-readable presentation state.
 */
export function formatDocumentStatus(status: string): {
  label: string;
  badgeClass: string;
  isReady: boolean;
  isProcessing: boolean;
  isFailed: boolean;
  description: string;
} {
  const norm = (status || "").toUpperCase();
  switch (norm) {
    case "PROCESSED":
      return {
        label: "Ready for Learning",
        badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-300",
        isReady: true,
        isProcessing: false,
        isFailed: false,
        description: "Text extracted and chunked. Ready to ground learning sessions.",
      };
    case "PROCESSING":
      return {
        label: "Processing Text...",
        badgeClass: "bg-amber-50 text-amber-700 border-amber-300 animate-pulse",
        isReady: false,
        isProcessing: true,
        isFailed: false,
        description: "Extracting text passages and indexing chunks.",
      };
    case "UPLOADED":
      return {
        label: "Uploaded",
        badgeClass: "bg-cyan-50 text-cyan-700 border-cyan-300",
        isReady: false,
        isProcessing: false,
        isFailed: false,
        description: "Uploaded to storage. Ready to begin text extraction.",
      };
    case "FAILED":
      return {
        label: "Extraction Failed",
        badgeClass: "bg-rose-50 text-rose-700 border-rose-300",
        isReady: false,
        isProcessing: false,
        isFailed: true,
        description: "Text extraction encountered an issue. You can retry processing.",
      };
    default:
      return {
        label: status || "Unknown",
        badgeClass: "bg-slate-50 text-slate-700 border-slate-300",
        isReady: false,
        isProcessing: false,
        isFailed: false,
        description: "Status pending verification.",
      };
  }
}

/**
 * List user's documents with pagination.
 */
export async function listDocuments(page = 1, pageSize = 20): Promise<DocumentListResponse> {
  return apiClient<DocumentListResponse>("/documents", {
    params: { page, page_size: pageSize },
  });
}

/**
 * Get single document details.
 */
export async function getDocument(documentId: string): Promise<DocumentItem> {
  return apiClient<DocumentItem>(`/documents/${documentId}`);
}

/**
 * Upload a document using authenticated multipart request.
 */
export async function uploadDocument(file: File): Promise<DocumentItem> {
  const validation = validateDocumentFile(file);
  if (!validation.valid) {
    throw new Error(validation.error || "Invalid file");
  }

  const formData = new FormData();
  formData.append("file", file);

  return apiClient<DocumentItem>("/documents", {
    method: "POST",
    body: formData,
  });
}

/**
 * Delete a document permanently.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  return apiClient<void>(`/documents/${documentId}`, {
    method: "DELETE",
  });
}

/**
 * Trigger text extraction / processing for an uploaded document.
 */
export async function processDocument(documentId: string): Promise<DocumentItem> {
  return apiClient<DocumentItem>(`/documents/${documentId}/process`, {
    method: "POST",
  });
}
