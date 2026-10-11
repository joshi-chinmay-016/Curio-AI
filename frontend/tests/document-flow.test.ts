import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  getDocument,
  deleteDocument,
  processDocument,
  formatDocumentStatus,
  formatFileSize,
} from "../services/documentService";
import { startSession } from "../services/sessionService";
import { useSessionStore } from "../stores/sessionStore";
import { ChatMessage, SourceCitation } from "../types/session";

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

describe("Document Flow, Deletion & Grounding Workspace Tests", () => {
  const originalFetch = globalThis.fetch;
  let recordedRequests: Array<{ url: string; options: RequestInit }> = [];

  beforeEach(() => {
    mockStorage.clear();
    recordedRequests = [];
    useSessionStore.getState().reset();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  // 1. Authenticated Deletion with 204 No Content
  test("1. Authenticated deletion: sends DELETE /documents/{id} with Bearer token and handles 204", async () => {
    mockStorage.setItem("curio_access_token", "user_secret_jwt_token");

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      recordedRequests.push({ url, options: init || {} });
      if (init?.method === "DELETE" && url.includes("/documents/doc-uuid-999")) {
        return new Response(null, { status: 204 });
      }
      return new Response("Not Found", { status: 404 });
    }) as any;

    await deleteDocument("doc-uuid-999");

    assert.equal(recordedRequests.length, 1);
    assert.match(recordedRequests[0].url, /\/api\/v1\/documents\/doc-uuid-999/);
    assert.equal(recordedRequests[0].options.method, "DELETE");
    const headers = recordedRequests[0].options.headers as Record<string, string>;
    assert.equal(headers["Authorization"], "Bearer user_secret_jwt_token");
  });

  // 2. Deletion failure propagation (403 Forbidden / Not Owner)
  test("2. Deletion rejection: throws on 403 Forbidden so UI does not remove document", async () => {
    mockStorage.setItem("curio_access_token", "other_user_token");

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      return new Response(
        JSON.stringify({ detail: "You do not have permission to delete this document" }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      );
    }) as any;

    await assert.rejects(
      async () => {
        await deleteDocument("unowned-doc-123");
      },
      (err: any) => {
        assert.equal(err.status, 403);
        assert.match(err.message, /permission/i);
        return true;
      }
    );
  });

  // 3. Deletion conflict response (409 Conflict when attached to active session)
  test("3. Deletion conflict: handles 409 Conflict cleanly", async () => {
    mockStorage.setItem("curio_access_token", "user_token");

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      return new Response(
        JSON.stringify({ detail: "Document is currently locked by active session" }),
        { status: 409, headers: { "Content-Type": "application/json" } }
      );
    }) as any;

    await assert.rejects(
      async () => {
        await deleteDocument("active-doc-456");
      },
      (err: any) => {
        assert.equal(err.status, 409);
        assert.match(err.message, /active session/i);
        return true;
      }
    );
  });

  // 4. Document details retrieval
  test("4. getDocument: retrieves document metadata and chunk count", async () => {
    mockStorage.setItem("curio_access_token", "user_jwt");

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      return new Response(
        JSON.stringify({
          document_id: "doc-abc-123",
          filename: "Quantum_Computing_Notes.pdf",
          file_size: 2048576,
          mime_type: "application/pdf",
          status: "PROCESSED",
          page_count: 14,
          chunk_count: 42,
          created_at: "2026-10-11T12:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }) as any;

    const doc = await getDocument("doc-abc-123");
    assert.equal(doc.document_id, "doc-abc-123");
    assert.equal(doc.filename, "Quantum_Computing_Notes.pdf");
    assert.equal(doc.chunk_count, 42);
    assert.equal(doc.page_count, 14);
    assert.equal(formatFileSize(doc.file_size), "2.0 MB");

    const statusPresentation = formatDocumentStatus(doc.status);
    assert.equal(statusPresentation.isReady, true);
    assert.equal(statusPresentation.isProcessing, false);
    assert.equal(statusPresentation.label, "Ready for Learning");
  });

  // 5. Document text extraction trigger
  test("5. processDocument: issues POST /documents/{id}/process", async () => {
    mockStorage.setItem("curio_access_token", "user_jwt");

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      return new Response(
        JSON.stringify({
          document_id: "doc-abc-123",
          filename: "Notes.txt",
          file_size: 1024,
          mime_type: "text/plain",
          status: "PROCESSING",
          page_count: 1,
          chunk_count: 0,
          created_at: "2026-10-11T12:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }) as any;

    const result = await processDocument("doc-abc-123");
    assert.equal(result.status, "PROCESSING");
    assert.match(recordedRequests[0].url, /\/api\/v1\/documents\/doc-abc-123\/process/);
    assert.equal(recordedRequests[0].options.method, "POST");
  });

  // 6. Grounded learning session creation
  test("6. startSession with document: attaches documentId and sourceType to session", async () => {
    mockStorage.setItem("curio_access_token", "user_jwt");

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      return new Response(
        JSON.stringify({
          session_id: "sess-rag-777",
          topic: body.topic || "Quantum Computing",
          status: "IN_PROGRESS",
          source_type: body.source_type,
          document_id: body.document_id,
          created_at: "2026-10-11T12:00:00Z",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } }
      );
    }) as any;

    const sessionRes = await startSession("Quantum Computing", {
      sourceType: "DOCUMENT",
      documentId: "doc-abc-123",
    });

    assert.equal(sessionRes.sessionId, "sess-rag-777");
    assert.equal(sessionRes.documentId, "doc-abc-123");

    // Verify session store integration
    const store = useSessionStore.getState();
    store.setTopic("Quantum Computing", sessionRes.sessionId, "DOCUMENT", sessionRes.documentId);

    const updatedState = useSessionStore.getState();
    assert.equal(updatedState.topicName, "Quantum Computing");
    assert.equal(updatedState.sourceType, "DOCUMENT");
    assert.equal(updatedState.documentId, "doc-abc-123");
  });

  // 7. Source Citation typing & contract
  test("7. ChatMessage citations: supports typed source citations when present without fabrication", () => {
    const citation: SourceCitation = {
      documentId: "doc-1",
      documentName: "Quantum_Notes.pdf",
      pageNumber: 3,
      snippet: "Superposition allows qubits to exist in linear combinations of states.",
    };

    const messageWithCitation: ChatMessage = {
      id: "msg-101",
      role: "curio",
      type: "question",
      content: "How does superposition enable exponential parallelism in Shor's algorithm?",
      timestamp: "12:05 PM",
      turnNumber: 2,
      mode: "STUDENT",
      citations: [citation],
    };

    assert.equal(messageWithCitation.citations?.length, 1);
    assert.equal(messageWithCitation.citations?.[0].documentName, "Quantum_Notes.pdf");
    assert.equal(messageWithCitation.citations?.[0].pageNumber, 3);

    // Message without citation has undefined or empty citations (no synthetic fabrication)
    const generalMessage: ChatMessage = {
      id: "msg-102",
      role: "curio",
      type: "question",
      content: "Can you explain recursion simply?",
      timestamp: "12:06 PM",
      mode: "STUDENT",
    };

    assert.equal(generalMessage.citations, undefined);
  });

  // 8. User isolation: switching auth tokens transmits correct credentials
  test("8. User isolation: API client isolates requests based on active user token", async () => {
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      return new Response(JSON.stringify({ documents: [], total: 0, page: 1, page_size: 20 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as any;

    // User A request
    mockStorage.setItem("curio_access_token", "user_A_token");
    const { listDocuments } = await import("../services/documentService");
    await listDocuments(1, 10);
    const headersA = recordedRequests[0].options.headers as Record<string, string>;
    assert.equal(headersA["Authorization"], "Bearer user_A_token");

    // User logs out / switches to User B
    mockStorage.setItem("curio_access_token", "user_B_token");
    await listDocuments(1, 10);
    const headersB = recordedRequests[1].options.headers as Record<string, string>;
    assert.equal(headersB["Authorization"], "Bearer user_B_token");
    assert.notEqual(headersA["Authorization"], headersB["Authorization"]);
  });
});
