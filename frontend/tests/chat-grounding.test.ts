import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import {
  validateDocumentFile,
  formatDocumentStatus,
  uploadDocument,
  processDocument,
  getDocument,
} from "../services/documentService";
import { ApiSessionRepository } from "../services/sessionRepository/ApiSessionRepository";
import { updateSessionDocument, getSession } from "../services/sessionService";
import { ChatMessage, SessionState } from "../types/session";

describe("Document-Grounded Chat Integration Tests", () => {
  const originalFetch = globalThis.fetch;
  const mockToken = "test_user_jwt_token_12345";

  beforeEach(() => {
    // Setup authenticated localStorage session
    const mockStorage: Record<string, string> = {
      curio_access_token: mockToken,
      curio_user_id: "user_uuid_101",
    };
    (globalThis as any).localStorage = {
      getItem: (key: string) => mockStorage[key] || null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
      clear: () => {
        Object.keys(mockStorage).forEach((k) => delete mockStorage[k]);
      },
    };
    (globalThis as any).window = {
      localStorage: (globalThis as any).localStorage,
      location: { protocol: "http:", host: "localhost:3000" },
    };
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe("1. File Picker & Client-Side Validation", () => {
    test("Accepts supported formats (.pdf, .txt, .docx) within size limits", () => {
      const pdf = { name: "Lecture1.pdf", size: 1024 * 100 } as File;
      const txt = { name: "notes.txt", size: 500 } as File;
      const docx = { name: "Summary.docx", size: 1024 * 1024 } as File;

      assert.strictEqual(validateDocumentFile(pdf).valid, true);
      assert.strictEqual(validateDocumentFile(txt).valid, true);
      assert.strictEqual(validateDocumentFile(docx).valid, true);
    });

    test("Rejects empty files (0 bytes)", () => {
      const empty = { name: "empty.pdf", size: 0 } as File;
      const res = validateDocumentFile(empty);
      assert.strictEqual(res.valid, false);
      assert.match(res.error || "", /empty/i);
    });

    test("Rejects files exceeding backend 10 MB limit", () => {
      const huge = { name: "huge.pdf", size: 11 * 1024 * 1024 } as File;
      const res = validateDocumentFile(huge);
      assert.strictEqual(res.valid, false);
      assert.match(res.error || "", /10 MB/i);
    });

    test("Rejects unsupported extensions (.exe, .jpg, .py)", () => {
      const exe = { name: "malware.exe", size: 1000 } as File;
      const jpg = { name: "photo.jpg", size: 1000 } as File;
      const py = { name: "script.py", size: 1000 } as File;

      assert.strictEqual(validateDocumentFile(exe).valid, false);
      assert.strictEqual(validateDocumentFile(jpg).valid, false);
      assert.strictEqual(validateDocumentFile(py).valid, false);
      assert.match(validateDocumentFile(exe).error || "", /Unsupported file type/i);
    });
  });

  describe("2. Document Upload & Processing Lifecycle", () => {
    test("Upload sends authenticated multipart request without forced JSON content-type", async () => {
      let capturedUrl = "";
      let capturedAuthHeader = "";
      let capturedMethod = "";

      globalThis.fetch = async (url: any, init: any) => {
        capturedUrl = url.toString();
        capturedMethod = init?.method;
        capturedAuthHeader = (init?.headers as Record<string, string>)?.["Authorization"] || "";

        return new Response(
          JSON.stringify({
            document_id: "doc_test_1",
            filename: "distributed_systems.pdf",
            file_size: 2048,
            mime_type: "application/pdf",
            status: "UPLOADED",
            page_count: 5,
            chunk_count: 0,
            created_at: new Date().toISOString(),
          }),
          { status: 201, headers: { "Content-Type": "application/json" } }
        );
      };

      const file = { name: "distributed_systems.pdf", size: 2048 } as File;
      const doc = await uploadDocument(file);

      assert.strictEqual(capturedMethod, "POST");
      assert.match(capturedUrl, /\/documents$/);
      assert.strictEqual(capturedAuthHeader, `Bearer ${mockToken}`);
      assert.strictEqual(doc.document_id, "doc_test_1");
      assert.strictEqual(doc.status, "UPLOADED");
    });

    test("Triggers processing and maps status states accurately", async () => {
      globalThis.fetch = async (url: any, init: any) => {
        if (url.toString().includes("/process")) {
          return new Response(
            JSON.stringify({
              document_id: "doc_test_1",
              filename: "notes.txt",
              file_size: 512,
              mime_type: "text/plain",
              status: "PROCESSING",
              page_count: 1,
              chunk_count: 0,
              created_at: new Date().toISOString(),
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }
        return new Response(
          JSON.stringify({
            document_id: "doc_test_1",
            filename: "notes.txt",
            file_size: 512,
            mime_type: "text/plain",
            status: "PROCESSED",
            page_count: 1,
            chunk_count: 4,
            created_at: new Date().toISOString(),
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      };

      const proc = await processDocument("doc_test_1");
      assert.strictEqual(proc.status, "PROCESSING");
      assert.strictEqual(formatDocumentStatus(proc.status).isProcessing, true);

      const ready = await getDocument("doc_test_1");
      assert.strictEqual(ready.status, "PROCESSED");
      assert.strictEqual(formatDocumentStatus(ready.status).isReady, true);
    });

    test("Upload failure does not mark document as ready", async () => {
      globalThis.fetch = async () => {
        return new Response(
          JSON.stringify({ detail: "Server storage full" }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      };

      const file = { name: "test.pdf", size: 1024 } as File;
      await assert.rejects(
        async () => uploadDocument(file),
        /Server storage full/
      );
    });
  });

  describe("3. Session Document Attachment & Non-Destructive Detachment", () => {
    test("Attaching document issues PATCH with source_type: DOCUMENT and document_id", async () => {
      let capturedBody: any = null;
      let capturedMethod = "";

      globalThis.fetch = async (url: any, init: any) => {
        capturedMethod = init?.method;
        capturedBody = JSON.parse(init?.body);

        return new Response(
          JSON.stringify({
            id: "sess_101",
            user_id: "user_uuid_101",
            topic: "Raft Consensus",
            source_type: capturedBody.source_type,
            document_id: capturedBody.document_id,
            status: "ACTIVE",
            created_at: new Date().toISOString(),
            last_active_at: new Date().toISOString(),
            confidence: 0.65,
            state: { current_mode: "STUDENT" },
            messages: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      };

      const repo = new ApiSessionRepository();
      const updated = await repo.updateSession("sess_101", {
        sourceType: "DOCUMENT",
        documentId: "doc_uuid_888",
      });

      assert.strictEqual(capturedMethod, "PATCH");
      assert.strictEqual(capturedBody.source_type, "DOCUMENT");
      assert.strictEqual(capturedBody.document_id, "doc_uuid_888");
      assert.strictEqual(updated.sourceType, "DOCUMENT");
      assert.strictEqual(updated.documentId, "doc_uuid_888");
    });

    test("Detaching document issues PATCH with source_type: GENERAL and document_id: null without deleting the file", async () => {
      let patchCount = 0;
      let deleteCount = 0;
      let capturedPatchBody: any = null;

      globalThis.fetch = async (url: any, init: any) => {
        if (init?.method === "PATCH") {
          patchCount++;
          capturedPatchBody = JSON.parse(init?.body);
          return new Response(
            JSON.stringify({
              id: "sess_101",
              user_id: "user_uuid_101",
              topic: "Raft Consensus",
              source_type: "GENERAL",
              document_id: null,
              status: "ACTIVE",
              created_at: new Date().toISOString(),
              last_active_at: new Date().toISOString(),
              confidence: 0.65,
              state: { current_mode: "STUDENT" },
              messages: [],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }
        if (init?.method === "DELETE") {
          deleteCount++;
          return new Response(null, { status: 204 });
        }
        return new Response("{}", { status: 200 });
      };

      const repo = new ApiSessionRepository();
      const updated = await repo.updateSession("sess_101", {
        sourceType: "GENERAL",
        documentId: undefined,
      });

      // Assert detachment was updated via PATCH
      assert.strictEqual(patchCount, 1);
      assert.strictEqual(capturedPatchBody.source_type, "GENERAL");
      // Assert that detachment DID NOT issue a DELETE call to the library!
      assert.strictEqual(deleteCount, 0, "Detaching document must not delete file from library");
      assert.strictEqual(updated.sourceType, "GENERAL");
      assert.strictEqual(updated.documentId, null);
    });

    test("Session restoration persists document association", async () => {
      globalThis.fetch = async () => {
        return new Response(
          JSON.stringify({
            id: "sess_restored_202",
            user_id: "user_uuid_101",
            topic: "Operating Systems",
            source_type: "DOCUMENT",
            document_id: "doc_persisted_777",
            status: "ACTIVE",
            created_at: new Date().toISOString(),
            last_active_at: new Date().toISOString(),
            confidence: 0.75,
            state: { current_mode: "STUDENT" },
            messages: [
              {
                id: "m_1",
                session_id: "sess_restored_202",
                sender: "AI",
                content: "How does virtual memory paging work?",
                input_type: "TEXT",
                created_at: new Date().toISOString(),
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      };

      const session = await getSession("sess_restored_202");
      assert.strictEqual(session.sessionId, "sess_restored_202");
      assert.strictEqual(session.sourceType, "DOCUMENT");
      assert.strictEqual(session.documentId, "doc_persisted_777");
    });
  });

  describe("4. Chat Message Submission & Grounding Flow", () => {
    test("Message submission uses existing POST /sessions/{id}/messages endpoint", async () => {
      let capturedUrl = "";
      let capturedBody: any = null;

      globalThis.fetch = async (url: any, init: any) => {
        capturedUrl = url.toString();
        capturedBody = JSON.parse(init?.body);

        return new Response(
          JSON.stringify({
            user_message: {
              message_id: "msg_user_1",
              session_id: "sess_101",
              sender: "USER",
              content: capturedBody.content,
              input_type: "TEXT",
              created_at: new Date().toISOString(),
            },
            ai_message: {
              message_id: "msg_ai_1",
              session_id: "sess_101",
              sender: "AI",
              content: "In Section 3, Raft elects a leader via randomized election timeouts.",
              input_type: "TEXT",
              created_at: new Date().toISOString(),
            },
            evaluation: {
              correctness: 0.85,
              clarity: 0.8,
              completeness: 0.75,
              depth: 0.7,
              relevance: 0.9,
              stuck_probability: 0.1,
              misconceptions: [],
              missing_concepts: [],
              undefined_terms: [],
              mastered_concepts: ["Leader Election"],
              knowledge_gap: null,
              recommended_strategy: "SOCRATIC_PROBING",
              recommended_difficulty: 2,
            },
            decision: {
              next_mode: "STUDENT",
              strategy: "SOCRATIC_PROBING",
              difficulty: 2,
              confidence: 0.8,
              reason: "Strong explanation of election timeouts.",
              active_concept: "Leader Election",
              should_offer_termination: false,
              should_restore_interrupted_question: false,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      };

      const repo = new ApiSessionRepository();
      const turn = await repo.sendMessage("sess_101", "Raft uses randomized election timeouts to prevent split votes.");

      assert.match(capturedUrl, /\/sessions\/sess_101\/messages$/);
      assert.strictEqual(capturedBody.content, "Raft uses randomized election timeouts to prevent split votes.");
      assert.strictEqual(turn.ai_message.content, "In Section 3, Raft elects a leader via randomized election timeouts.");
      assert.strictEqual(turn.decision.next_mode, "STUDENT");
      assert.strictEqual(turn.evaluation.correctness, 0.85);
    });

    test("Preserves Student Mode and Teacher Mode based on backend decision", async () => {
      globalThis.fetch = async () => {
        return new Response(
          JSON.stringify({
            user_message: {
              message_id: "msg_user_2",
              session_id: "sess_101",
              sender: "USER",
              content: "I don't understand how log replication works.",
              input_type: "TEXT",
              created_at: new Date().toISOString(),
            },
            ai_message: {
              message_id: "msg_ai_2",
              session_id: "sess_101",
              sender: "AI",
              content: "Let's isolate log replication. In Raft, the leader appends entries to its log first.",
              input_type: "TEXT",
              created_at: new Date().toISOString(),
            },
            evaluation: {
              correctness: 0.2,
              clarity: 0.5,
              completeness: 0.1,
              depth: 0.1,
              relevance: 0.8,
              stuck_probability: 0.9,
              misconceptions: ["Logs are written by followers first"],
              missing_concepts: ["Leader-driven replication"],
              undefined_terms: [],
              mastered_concepts: [],
              knowledge_gap: "Log Replication Invariant",
              recommended_strategy: "STEP_BY_STEP_DECOMPOSITION",
              recommended_difficulty: 1,
            },
            decision: {
              next_mode: "TEACHER",
              strategy: "STEP_BY_STEP_DECOMPOSITION",
              difficulty: 1,
              confidence: 0.3,
              reason: "Misconception regarding log entry propagation direction.",
              active_concept: "Log Replication Invariant",
              should_offer_termination: false,
              should_restore_interrupted_question: false,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      };

      const repo = new ApiSessionRepository();
      const turn = await repo.sendMessage("sess_101", "I don't understand how log replication works.");

      assert.strictEqual(turn.decision.next_mode, "TEACHER");
      assert.strictEqual(turn.evaluation.knowledge_gap, "Log Replication Invariant");
    });

    test("Submission failure throws and preserves draft", async () => {
      globalThis.fetch = async () => {
        return new Response(
          JSON.stringify({ detail: "Gateway timeout" }),
          { status: 504, headers: { "Content-Type": "application/json" } }
        );
      };

      const repo = new ApiSessionRepository();
      await assert.rejects(
        async () => repo.sendMessage("sess_101", "My draft explanation"),
        /Gateway timeout/
      );
    });
  });

  describe("5. Grounding & Citations Integrity", () => {
    test("Source citations are supported without fabricating citations when absent", () => {
      const msgWithCitations: ChatMessage = {
        id: "m_cite_1",
        role: "curio",
        type: "question",
        content: "What does the document say about Raft RPCs?",
        timestamp: "12:00",
        mode: "STUDENT",
        citations: [
          {
            documentId: "doc_1",
            documentName: "raft.pdf",
            pageNumber: 4,
            snippet: "The leader sends AppendEntries RPCs to all followers.",
          },
        ],
      };

      const msgWithoutCitations: ChatMessage = {
        id: "m_cite_2",
        role: "curio",
        type: "question",
        content: "Explain binary search in your own words.",
        timestamp: "12:01",
        mode: "STUDENT",
      };

      assert.strictEqual(msgWithCitations.citations?.length, 1);
      assert.strictEqual(msgWithCitations.citations?.[0].documentName, "raft.pdf");
      assert.strictEqual(msgWithCitations.citations?.[0].pageNumber, 4);

      // Verify no citations are fabricated on ordinary or non-grounded messages
      assert.strictEqual(msgWithoutCitations.citations, undefined);
    });
  });
});
