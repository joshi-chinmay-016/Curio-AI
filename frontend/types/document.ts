export type DocumentStatus = "UPLOADED" | "PROCESSING" | "PROCESSED" | "FAILED";

export interface DocumentItem {
  document_id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  status: DocumentStatus | string;
  page_count: number | null;
  chunk_count: number;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
}

export type DocumentFilterStatus = "ALL" | "READY" | "PROCESSING" | "FAILED";
export type DocumentSortOption = "NEWEST" | "OLDEST" | "NAME" | "SIZE";
