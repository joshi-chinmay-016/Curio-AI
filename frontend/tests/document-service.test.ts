import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  listDocuments,
  getDocument,
  uploadDocument,
  deleteDocument,
  processDocument,
  validateDocumentFile,
  formatFileSize,
  formatDocumentStatus,
  MAX_UPLOAD_SIZE,
} from "../services/documentService";

class LocalStorageMock {
  private store: Record<string, string> = {};
  getItem(key: string): string | null {
    return this.store[key] ?? null;
  }
  setItem(key: string, value: string): void {
    this.store[key] = String(value);
  }
  removeItem(key: string): void {
    delete this.store[key];
  }
  clear(): void {
    this.store = {};
  }
}

const mockStorage = new LocalStorageMock();
(globalThis as any).window = globalThis;
(globalThis as any).localStorage = mockStorage;
(globalThis as any).sessionStorage = mockStorage;

// Helper to create mock File in Node environment
function createMockFile(name: string, sizeBytes: number, type = "application/pdf"): File {
  const buffer = new Uint8Array(sizeBytes);
  return new File([buffer], name, { type });
}

describe("Document Service and File Validation Tests", () => {
  const originalFetch = globalThis.fetch;
  let recordedRequests: Array<{ url: string; options: RequestInit }> = [];

  beforeEach(() => {
    mockStorage.clear();
    recordedRequests = [];
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  // 1. Client-side file validation
  test("1. Client-side validation: Rejects empty file (0 bytes)", () => {
    const emptyFile = createMockFile("notes.pdf", 0, "application/pdf");
    const result = validateDocumentFile(emptyFile);
    assert.equal(result.valid, false);
    assert.match(result.error || "", /empty/i);
  });

  test("2. Client-side validation: Rejects files exceeding 100 MB", () => {
    const largeFile = createMockFile("large_textbook.pdf", MAX_UPLOAD_SIZE + 1024, "application/pdf");
    const result = validateDocumentFile(largeFile);
    assert.equal(result.valid, false);
    assert.match(result.error || "", /100 MB/i);
  });

  test("3. Client-side validation: Rejects unsupported file extensions", () => {
    const scriptFile = createMockFile("exploit.exe", 1024, "application/octet-stream");
    const result = validateDocumentFile(scriptFile);
    assert.equal(result.valid, false);
    assert.match(result.error || "", /Unsupported file type/i);
  });

  test("4. Client-side validation: Accepts valid .pdf, .txt, and .docx files", () => {
    const pdf = createMockFile("biology.pdf", 2048, "application/pdf");
    assert.equal(validateDocumentFile(pdf).valid, true);

    const txt = createMockFile("notes.txt", 1024, "text/plain");
    assert.equal(validateDocumentFile(txt).valid, true);

    const docx = createMockFile(
      "lecture.docx",
      4096,
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    );
    assert.equal(validateDocumentFile(docx).valid, true);
  });

  // 2. Authenticated listDocuments
  test("5. listDocuments sends authenticated request with pagination parameters", async () => {
    mockStorage.setItem("curio_access_token", "test-doc-token");

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      const headers = (init?.headers || {}) as Record<string, string>;
      assert.equal(headers["Authorization"], "Bearer test-doc-token");

      return new Response(
        JSON.stringify({
          documents: [
            {
              document_id: "doc-123",
              filename: "sample.pdf",
              file_size: 10240,
              mime_type: "application/pdf",
              status: "PROCESSED",
              page_count: 5,
              chunk_count: 12,
              created_at: "2026-10-11T12:00:00Z",
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    };

    const res = await listDocuments(1, 20);
    assert.equal(res.total, 1);
    assert.equal(res.documents[0].filename, "sample.pdf");
    assert.match(recordedRequests[0].url, /page=1/);
    assert.match(recordedRequests[0].url, /page_size=20/);
  });

  // 3. Authenticated getDocument
  test("6. getDocument retrieves single document details", async () => {
    mockStorage.setItem("curio_access_token", "test-doc-token");

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      return new Response(
        JSON.stringify({
          document_id: "doc-999",
          filename: "operating_systems.pdf",
          file_size: 204800,
          mime_type: "application/pdf",
          status: "PROCESSED",
          page_count: 45,
          chunk_count: 110,
          created_at: "2026-10-11T14:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    };

    const doc = await getDocument("doc-999");
    assert.equal(doc.document_id, "doc-999");
    assert.equal(doc.chunk_count, 110);
    assert.match(recordedRequests[0].url, /\/documents\/doc-999/);
  });

  // 4. Authenticated uploadDocument
  test("7. uploadDocument sends multipart FormData without forced JSON Content-Type", async () => {
    mockStorage.setItem("curio_access_token", "test-doc-token");

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      const headers = (init?.headers || {}) as Record<string, string>;

      // Authorization header must be present
      assert.equal(headers["Authorization"], "Bearer test-doc-token");
      // Content-Type must NOT be application/json for FormData
      assert.notEqual(headers["Content-Type"], "application/json");

      return new Response(
        JSON.stringify({
          document_id: "new-doc-id",
          filename: "syllabus.pdf",
          file_size: 4096,
          mime_type: "application/pdf",
          status: "UPLOADED",
          page_count: null,
          chunk_count: 0,
          created_at: "2026-10-11T15:00:00Z",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } }
      );
    };

    const file = createMockFile("syllabus.pdf", 4096, "application/pdf");
    const uploaded = await uploadDocument(file);
    assert.equal(uploaded.document_id, "new-doc-id");
    assert.equal(uploaded.status, "UPLOADED");
  });

  // 5. Authenticated deleteDocument
  test("8. deleteDocument sends DELETE request and handles 204 No Content cleanly", async () => {
    mockStorage.setItem("curio_access_token", "test-doc-token");

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      assert.equal(init?.method, "DELETE");
      return new Response(null, { status: 204 });
    };

    await deleteDocument("doc-to-delete");
    assert.equal(recordedRequests[0].options.method, "DELETE");
    assert.match(recordedRequests[0].url, /\/documents\/doc-to-delete/);
  });

  // 6. Authenticated processDocument
  test("9. processDocument sends POST /process and returns updated status", async () => {
    mockStorage.setItem("curio_access_token", "test-doc-token");

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      assert.equal(init?.method, "POST");
      return new Response(
        JSON.stringify({
          document_id: "doc-proc-1",
          filename: "research.pdf",
          file_size: 8192,
          mime_type: "application/pdf",
          status: "PROCESSED",
          page_count: 3,
          chunk_count: 8,
          created_at: "2026-10-11T12:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    };

    const res = await processDocument("doc-proc-1");
    assert.equal(res.status, "PROCESSED");
    assert.equal(res.page_count, 3);
    assert.match(recordedRequests[0].url, /\/documents\/doc-proc-1\/process/);
  });

  // 7. Utility formatters
  test("10. Utility formatters correctly map bytes and backend statuses", () => {
    assert.equal(formatFileSize(0), "0 B");
    assert.equal(formatFileSize(512), "512 B");
    assert.equal(formatFileSize(2048), "2.0 KB");
    assert.equal(formatFileSize(5 * 1024 * 1024), "5.0 MB");

    const ready = formatDocumentStatus("PROCESSED");
    assert.equal(ready.isReady, true);
    assert.equal(ready.isProcessing, false);

    const proc = formatDocumentStatus("PROCESSING");
    assert.equal(proc.isProcessing, true);

    const failed = formatDocumentStatus("FAILED");
    assert.equal(failed.isFailed, true);
  });
});
