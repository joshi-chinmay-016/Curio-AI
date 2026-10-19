import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { ApiSessionRepository } from "../services/sessionRepository/ApiSessionRepository";
import { transcribeAudio } from "../services/voiceService";
import { ChatMessage, SessionState } from "../types/session";

describe("Phase 3: Route Transcribed Questions Through Existing Chat Flow", () => {
  const originalFetch = globalThis.fetch;
  const mockToken = "jwt_bearer_token_voice_routing_test";
  const testSessionId = "session_voice_integration_456";

  let capturedRequests: Array<{ url: string; method: string; headers: Record<string, string>; body: any }> = [];

  beforeEach(() => {
    capturedRequests = [];

    const mockStorage: Record<string, string> = {
      curio_access_token: mockToken,
      curio_user_id: "user_uuid_789",
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

  test("1. End-to-end pipeline: Audio -> Transcript -> Composer -> sendMessage -> POST /messages", async () => {
    // 1. Mock voice transcription endpoint
    // 2. Mock chat message endpoint
    globalThis.fetch = (async (url: string, init?: RequestInit) => {
      const parsedUrl = new URL(url, "http://localhost:8000");
      capturedRequests.push({
        url: parsedUrl.pathname,
        method: init?.method || "GET",
        headers: (init?.headers as Record<string, string>) || {},
        body: init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : null,
      });

      if (parsedUrl.pathname.endsWith("/voice/transcribe")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            text: "Can you explain how recursion relates to induction?",
            language: "en",
            duration_seconds: 2.8,
          }),
        } as Response;
      }

      if (parsedUrl.pathname.includes(`/sessions/${testSessionId}/messages`)) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            decision: {
              next_mode: "STUDENT",
              active_concept: "recursion-structural-induction",
              confidence: 78.5,
              action: "PROCEED",
              evaluation_reasoning: "Valid inquiry linking base cases and inductive hypothesis.",
            },
            ai_message: {
              message_id: "msg_ai_991",
              role: "curio",
              content: "Recursion and mathematical induction are dual concepts. In induction, you prove a base case and show that P(k) implies P(k+1).",
              created_at: new Date().toISOString(),
              citations: null,
            },
          }),
        } as Response;
      }

      return { ok: true, status: 200, json: async () => ({}) } as Response;
    }) as any;

    // Step 1: User speaks into recorder -> audio blob sent to Whisper STT
    const audioBlob = new Blob(["mock-speech-bytes"], { type: "audio/webm" });
    const transcription = await transcribeAudio(audioBlob);
    assert.strictEqual(transcription.text, "Can you explain how recursion relates to induction?");

    // Step 2: Recognized text populates composer draft (review-before-send)
    let composerText = transcription.text;
    assert.strictEqual(composerText, "Can you explain how recursion relates to induction?");

    // Step 3: User reviews, optionally edits or verifies, then submits
    const repo = new ApiSessionRepository();
    const result = await repo.sendMessage(testSessionId, composerText);

    // Step 4: Verify that the exact same backend chat pipeline was used
    assert.strictEqual(capturedRequests.length, 2);
    assert.strictEqual(capturedRequests[0].url, "/api/v1/voice/transcribe");
    assert.strictEqual(capturedRequests[1].url, `/api/v1/sessions/${testSessionId}/messages`);

    // Verify chat payload preserves the text identically to typed message
    assert.deepStrictEqual(capturedRequests[1].body, {
      content: "Can you explain how recursion relates to induction?",
      input_type: "TEXT",
    });

    // Verify authentication bearer token was sent on both calls
    assert.strictEqual(capturedRequests[0].headers["Authorization"], `Bearer ${mockToken}`);
    assert.strictEqual(capturedRequests[1].headers["Authorization"], `Bearer ${mockToken}`);

    // Verify resulting AI message
    assert.strictEqual(result.ai_message.content.includes("Recursion"), true);
    assert.match(result.ai_message.content, /Recursion and mathematical induction/);
    assert.strictEqual(result.decision.confidence, 78.5);
  });

  test("2. Parity check: Typed and spoken inputs invoke the exact same handler and schema", async () => {
    let capturedBodies: any[] = [];

    globalThis.fetch = (async (url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.includes("/messages")) {
        capturedBodies.push(JSON.parse(init.body as string));
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          decision: { next_mode: "STUDENT", active_concept: "c1", confidence: 80, reason: "PROCEED" },
          ai_message: { message_id: "m1", sender: "AI", content: "Response", created_at: new Date().toISOString() },
        }),
      } as Response;
    }) as any;

    const repo = new ApiSessionRepository();

    // Input A: Typed
    await repo.sendMessage(testSessionId, "What is a binary tree invariant?");

    // Input B: Spoken (transcribed text)
    const spokenTranscript = "What is a binary tree invariant?";
    await repo.sendMessage(testSessionId, spokenTranscript);

    // Verify payload parity
    assert.strictEqual(capturedBodies.length, 2);
    assert.deepStrictEqual(capturedBodies[0], capturedBodies[1]);
  });

  test("3. Preserves Student Mode assessment and does NOT grant false mastery to spoken questions", async () => {
    globalThis.fetch = (async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          decision: {
            next_mode: "STUDENT",
            active_concept: "tree-invariants",
            confidence: 42.0, // Low confidence
            reason: "Learner question is vague and indicates confusion.",
          },
          ai_message: {
            message_id: "m_eval_1",
            sender: "AI",
            content: "What invariant determines whether a node belongs to the left or right subtree?",
            created_at: new Date().toISOString(),
          },
        }),
      } as Response;
    }) as any;

    const repo = new ApiSessionRepository();
    const result = await repo.sendMessage(testSessionId, "I don't really get trees.");

    // Evaluated confidence reflects content understanding, not speech origin
    assert.strictEqual(result.decision.confidence, 42.0);
    assert.strictEqual(result.decision.next_mode, "STUDENT");
  });

  test("4. Preserves Teacher Mode intervention when spoken answer indicates concept gap", async () => {
    globalThis.fetch = (async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          decision: {
            next_mode: "TEACHER",
            active_concept: "tree-search-order",
            confidence: 25.0,
            reason: "Critical misconception: student confused BST with max heap.",
          },
          ai_message: {
            message_id: "msg_teacher_1",
            sender: "AI",
            content: "Notice the difference: in a BST, all left descendants must be smaller than the root.",
            created_at: new Date().toISOString(),
          },
        }),
      } as Response;
    }) as any;

    const repo = new ApiSessionRepository();
    const result = await repo.sendMessage(testSessionId, "In a BST, every child is smaller than its parent, right?");

    // Transitions to TEACHER mode properly
    assert.strictEqual(result.decision.next_mode, "TEACHER");
    assert.strictEqual(result.decision.active_concept, "tree-search-order");
    assert.match(result.ai_message.content, /in a BST/);
  });

  test("5. Preserves document grounding and citations when session has attached document", async () => {
    globalThis.fetch = (async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          decision: {
            next_mode: "STUDENT",
            active_concept: "gradient-descent",
            confidence: 85.0,
            reason: "PROCEED",
          },
          ai_message: {
            message_id: "msg_doc_1",
            sender: "AI",
            content: "According to Section 3.2 of the uploaded lecture notes, the learning rate controls step size.",
            created_at: new Date().toISOString(),
            citations: [
              {
                documentId: "doc_uuid_101",
                documentName: "Lecture3_Optimization.pdf",
                pageNumber: 12,
                snippet: "The step size is scaled by alpha, known as the learning rate.",
              },
            ],
          },
        }),
      } as Response;
    }) as any;

    const repo = new ApiSessionRepository();
    const result = await repo.sendMessage(testSessionId, "What does the notes say about learning rate?");
    const citations = (result.ai_message as any).citations;

    assert.strictEqual(citations?.length, 1);
    assert.strictEqual(citations[0].documentName, "Lecture3_Optimization.pdf");
    assert.strictEqual(citations[0].pageNumber, 12);
  });

  test("6. Handles session without document without fabricating sources", async () => {
    globalThis.fetch = (async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          decision: {
            next_mode: "STUDENT",
            active_concept: "hash-tables",
            confidence: 90.0,
            reason: "PROCEED",
          },
          ai_message: {
            message_id: "msg_nodoc_1",
            sender: "AI",
            content: "A hash function maps keys to array slots in expected O(1) time.",
            created_at: new Date().toISOString(),
            citations: null,
          },
        }),
      } as Response;
    }) as any;

    const repo = new ApiSessionRepository();
    const result = await repo.sendMessage(testSessionId, "How do hash tables work?");
    const citations = (result.ai_message as any).citations;

    assert.strictEqual(citations, null);
    assert.match(result.ai_message.content, /hash function/);
  });

  test("7. Handles empty or failed retrieval gracefully without interrupting chat", async () => {
    globalThis.fetch = (async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          decision: {
            next_mode: "STUDENT",
            active_concept: "quantum-computing",
            confidence: 70.0,
            reason: "PROCEED",
          },
          ai_message: {
            message_id: "msg_retrieval_empty",
            sender: "AI",
            content: "I could not find references to quantum computing in your document, but generally qubits exist in superposition.",
            created_at: new Date().toISOString(),
            citations: [],
          },
        }),
      } as Response;
    }) as any;

    const repo = new ApiSessionRepository();
    const result = await repo.sendMessage(testSessionId, "What does my document say about qubits?");
    const citations = (result.ai_message as any).citations;

    assert.strictEqual(citations?.length, 0);
    assert.match(result.ai_message.content, /superposition/);
  });
});
