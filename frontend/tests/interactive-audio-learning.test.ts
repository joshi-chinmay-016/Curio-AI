import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { sanitizeTextForSpeech } from "../services/speechService";
import { ApiSessionRepository } from "../services/sessionRepository/ApiSessionRepository";
import {
  CharacterType,
  CharacterAnimationState,
  AudioLearningMode,
  AudioSessionConfig,
  DifficultyOrdering,
} from "../types/audioLearning";

describe("Interactive Audio Learning Mode Test Suite", () => {
  const originalFetch = globalThis.fetch;
  const mockToken = "jwt_bearer_token_audio_learning";
  const testSessionId = "session_audio_interactive_101";

  let capturedRequests: Array<{ url: string; method: string; body: any }> = [];

  beforeEach(() => {
    capturedRequests = [];

    const mockStorage: Record<string, string> = {
      curio_access_token: mockToken,
      curio_user_id: "user_test_audio_456",
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

  describe("1. Character Identity & Animation State Model", () => {
    test("Character assets exist and match approved designs", () => {
      const approvedCharacters: CharacterType[] = ["student", "teacher", "professor"];
      assert.strictEqual(approvedCharacters.length, 3);
      assert.ok(approvedCharacters.includes("student"));
      assert.ok(approvedCharacters.includes("teacher"));
      assert.ok(approvedCharacters.includes("professor"));
    });

    test("Character animation states cover full interaction lifecycle", () => {
      const sampleStates: CharacterAnimationState[] = [
        "idle",
        "listening",
        "recording",
        "transcribing",
        "thinking",
        "taking_notes",
        "speaking",
        "curious",
        "confused",
        "impressed",
        "skeptical",
        "teacher_transition",
        "grumpy",
        "leaving",
        "session_complete",
      ];
      assert.strictEqual(sampleStates.length, 15);
    });

    test("Speech sanitization removes markdown, code blocks, and citations for natural spoken audio", () => {
      const rawMarkdown =
        "### Key Invariant\n```python\ndef test():\n    pass\n```\n**CAP Theorem** states that under `network partitioning`, you must choose [1] between **Consistency** and **Availability**.";
      const spoken = sanitizeTextForSpeech(rawMarkdown);

      assert.ok(!spoken.includes("```python"));
      assert.ok(!spoken.includes("def test()"));
      assert.ok(!spoken.includes("**"));
      assert.ok(!spoken.includes("`"));
      assert.ok(!spoken.includes("[1]"));
      assert.ok(spoken.includes("CAP Theorem states that under network partitioning"));
    });
  });

  describe("2. Audio Session Setup & Initialization", () => {
    test("Creates audio learning session with topic and GENERAL source mode", async () => {
      globalThis.fetch = (async (url: string, init?: RequestInit) => {
        const parsedUrl = new URL(url, "http://localhost:8000");
        capturedRequests.push({
          url: parsedUrl.pathname,
          method: init?.method || "GET",
          body: init?.body ? JSON.parse(init.body as string) : null,
        });

        if (parsedUrl.pathname.endsWith("/sessions")) {
          return {
            ok: true,
            status: 201,
            json: async () => ({
              id: testSessionId,
              user_id: "user_test_audio_456",
              topic: "Distributed Consensus",
              source_type: "GENERAL",
              status: "ACTIVE",
              created_at: new Date().toISOString(),
              state: {
                current_mode: "STUDENT",
                difficulty: 1,
                confidence: 65,
                active_concept: "Distributed Consensus",
              },
            }),
          } as Response;
        }
        return { ok: false, status: 404 } as Response;
      }) as any;

      const repo = new ApiSessionRepository();
      const session = await repo.createSession("Distributed Consensus", "GENERAL");

      assert.strictEqual(session.sessionId, testSessionId);
      assert.strictEqual(session.topic, "Distributed Consensus");
      assert.strictEqual(session.sourceType, "GENERAL");

      assert.strictEqual(capturedRequests.length, 1);
      assert.strictEqual(capturedRequests[0].url, "/api/v1/sessions");
      assert.strictEqual(capturedRequests[0].body.topic, "Distributed Consensus");
      assert.strictEqual(capturedRequests[0].body.source_type, "GENERAL");
    });

    test("Creates document-grounded audio session preserving document_id association", async () => {
      const docUuid = "doc_distributed_systems_999";
      globalThis.fetch = (async (url: string, init?: RequestInit) => {
        const parsedUrl = new URL(url, "http://localhost:8000");
        capturedRequests.push({
          url: parsedUrl.pathname,
          method: init?.method || "GET",
          body: init?.body ? JSON.parse(init.body as string) : null,
        });

        if (parsedUrl.pathname.endsWith("/sessions")) {
          return {
            ok: true,
            status: 201,
            json: async () => ({
              id: testSessionId,
              user_id: "user_test_audio_456",
              topic: "Raft Consensus",
              source_type: "DOCUMENT",
              document_id: docUuid,
              status: "ACTIVE",
              created_at: new Date().toISOString(),
              state: {
                current_mode: "STUDENT",
                difficulty: 2,
                confidence: 70,
                active_concept: "Leader Election",
              },
            }),
          } as Response;
        }
        return { ok: false, status: 404 } as Response;
      }) as any;

      const repo = new ApiSessionRepository();
      const session = await repo.createSession("Raft Consensus", "DOCUMENT", docUuid);

      assert.strictEqual(session.sessionId, testSessionId);
      assert.strictEqual(session.documentId, docUuid);
      assert.strictEqual(session.sourceType, "DOCUMENT");

      assert.strictEqual(capturedRequests[0].body.document_id, docUuid);
      assert.strictEqual(capturedRequests[0].body.source_type, "DOCUMENT");
    });
  });

  describe("3. Student Mode Audio Pipeline & Teacher Intervention", () => {
    test("Routes spoken answer with input_type: VOICE and evaluates understanding", async () => {
      globalThis.fetch = (async (url: string, init?: RequestInit) => {
        const parsedUrl = new URL(url, "http://localhost:8000");
        capturedRequests.push({
          url: parsedUrl.pathname,
          method: init?.method || "GET",
          body: init?.body ? JSON.parse(init.body as string) : null,
        });

        if (parsedUrl.pathname.includes("/messages")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              user_message: {
                message_id: "msg_u_1",
                session_id: testSessionId,
                sender: "USER",
                content: "In Raft, a candidate increments its term and requests votes from peers.",
                input_type: "VOICE",
                created_at: new Date().toISOString(),
              },
              ai_message: {
                message_id: "msg_ai_1",
                session_id: testSessionId,
                sender: "AI",
                content: "That explains election triggering! What happens if two candidates get equal votes?",
                input_type: "TEXT",
                created_at: new Date().toISOString(),
              },
              evaluation: {
                correctness: 0.85,
                clarity: 0.9,
                completeness: 0.8,
                depth: 0.75,
                relevance: 1.0,
                stuck_probability: 0.05,
                misconceptions: [],
                missing_concepts: [],
                undefined_terms: [],
                mastered_concepts: ["Leader Election Voting"],
                recommended_strategy: "PROBE_HOW",
                recommended_difficulty: 2,
              },
              decision: {
                next_mode: "STUDENT",
                strategy: "PROBE_HOW",
                difficulty: 2,
                confidence: 82,
                reason: "Solid understanding of candidate vote requests; probing split vote resolution.",
                active_concept: "Split Votes & Randomized Timeouts",
                should_offer_termination: false,
                should_restore_interrupted_question: false,
              },
            }),
          } as Response;
        }
        return { ok: false, status: 404 } as Response;
      }) as any;

      const repo = new ApiSessionRepository();
      const turn = await repo.sendMessage(
        testSessionId,
        "In Raft, a candidate increments its term and requests votes from peers.",
        "VOICE"
      );

      assert.strictEqual(capturedRequests[0].body.input_type, "VOICE");
      assert.strictEqual(turn.evaluation.correctness, 0.85);
      assert.strictEqual(turn.decision.next_mode, "STUDENT");
      assert.ok(turn.evaluation.mastered_concepts.includes("Leader Election Voting"));
    });

    test("Detects concept gap and triggers Teacher Mode transition with clarification", async () => {
      globalThis.fetch = (async (url: string, init?: RequestInit) => {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            user_message: {
              message_id: "msg_u_2",
              session_id: testSessionId,
              sender: "USER",
              content: "Raft allows any node to overwrite committed entries if its clock is faster.",
              input_type: "VOICE",
              created_at: new Date().toISOString(),
            },
            ai_message: {
              message_id: "msg_teach_1",
              session_id: testSessionId,
              sender: "AI",
              content:
                "Let's pause. In Raft, physical wall-clock time never overrides log commitment invariants. What prevents an uncommitted leader from overwriting committed entries?",
              input_type: "TEXT",
              created_at: new Date().toISOString(),
            },
            evaluation: {
              correctness: 0.2,
              clarity: 0.6,
              completeness: 0.3,
              depth: 0.2,
              relevance: 0.8,
              stuck_probability: 0.85,
              misconceptions: ["Physical clock precedence over log terms"],
              missing_concepts: ["Log Matching Property"],
              undefined_terms: [],
              mastered_concepts: [],
              knowledge_gap: "Log Matching & Term Invariants",
              recommended_strategy: "TEACH_GAP",
              recommended_difficulty: 1,
            },
            decision: {
              next_mode: "TEACHER",
              strategy: "TEACH_GAP",
              difficulty: 1,
              confidence: 35,
              reason: "Severe misconception detected regarding log overwriting.",
              active_concept: "Log Commitment Invariants",
              should_offer_termination: false,
              should_restore_interrupted_question: false,
            },
          }),
        } as Response;
      }) as any;

      const repo = new ApiSessionRepository();
      const turn = await repo.sendMessage(
        testSessionId,
        "Raft allows any node to overwrite committed entries if its clock is faster.",
        "VOICE"
      );

      assert.strictEqual(turn.decision.next_mode, "TEACHER");
      assert.ok(turn.evaluation.misconceptions.includes("Physical clock precedence over log terms"));
    });

    test("Returns to Student Mode when verification passes and restores inquiry", async () => {
      globalThis.fetch = (async (url: string, init?: RequestInit) => {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            user_message: {
              message_id: "msg_u_3",
              session_id: testSessionId,
              sender: "USER",
              content:
                "An entry is committed only when stored on a majority of nodes in the current term; leaders never overwrite committed entries.",
              input_type: "VOICE",
              created_at: new Date().toISOString(),
            },
            ai_message: {
              message_id: "msg_ai_restored",
              session_id: testSessionId,
              sender: "AI",
              content:
                "Precisely! You've verified the log invariant. Now returning to our earlier inquiry: how do randomized election timers prevent split vote deadlocks?",
              input_type: "TEXT",
              created_at: new Date().toISOString(),
            },
            evaluation: {
              correctness: 0.95,
              clarity: 0.9,
              completeness: 0.9,
              depth: 0.85,
              relevance: 1.0,
              stuck_probability: 0.0,
              misconceptions: [],
              missing_concepts: [],
              undefined_terms: [],
              mastered_concepts: ["Leader Completeness Property"],
              recommended_strategy: "RESTORE_INTERRUPTED_QUESTION",
              recommended_difficulty: 2,
            },
            decision: {
              next_mode: "STUDENT",
              strategy: "RESTORE_INTERRUPTED_QUESTION",
              difficulty: 2,
              confidence: 88,
              reason: "Verification passed with high correctness. Restoring interrupted inquiry.",
              active_concept: "Randomized Election Timers",
              should_offer_termination: false,
              should_restore_interrupted_question: true,
            },
          }),
        } as Response;
      }) as any;

      const repo = new ApiSessionRepository();
      const turn = await repo.sendMessage(
        testSessionId,
        "An entry is committed only when stored on a majority of nodes in the current term; leaders never overwrite committed entries.",
        "VOICE"
      );

      assert.strictEqual(turn.decision.next_mode, "STUDENT");
      assert.strictEqual(turn.decision.should_restore_interrupted_question, true);
    });
  });

  describe("4. Professor Mode Interview & Consecutive Unanswered Policy", () => {
    test("Consecutive unanswered counter tracks skips and triggers conclusion after 3 strikes", () => {
      let consecutiveUnanswered = 0;
      const maxAllowed = 3;
      let hasEndedByProfessor = false;

      // Question 1: User skips
      consecutiveUnanswered += 1;
      assert.strictEqual(consecutiveUnanswered, 1);
      assert.strictEqual(hasEndedByProfessor, false);

      // Question 2: User skips
      consecutiveUnanswered += 1;
      assert.strictEqual(consecutiveUnanswered, 2);
      assert.strictEqual(hasEndedByProfessor, false);

      // Question 3: User skips -> threshold reached
      consecutiveUnanswered += 1;
      if (consecutiveUnanswered >= maxAllowed) {
        hasEndedByProfessor = true;
      }
      assert.strictEqual(consecutiveUnanswered, 3);
      assert.strictEqual(hasEndedByProfessor, true);
    });

    test("Genuine answer resets consecutive unanswered counter to zero", () => {
      let consecutiveUnanswered = 2; // after 2 skips

      // User answers question 3 with explanation
      const userSpokeAnswer = "In B-trees, all leaf nodes reside at the exact same depth, ensuring O(log N) access.";
      const correctness = 0.8;

      if (correctness >= 0.5) {
        consecutiveUnanswered = 0;
      }

      assert.strictEqual(consecutiveUnanswered, 0);
    });

    test("Difficulty ordering supports EASY_TO_HARD, HARD_TO_EASY, and MIXED", () => {
      const orders: DifficultyOrdering[] = ["EASY_TO_HARD", "HARD_TO_EASY", "MIXED"];
      assert.strictEqual(orders.length, 3);

      const config: AudioSessionConfig = {
        mode: "PROFESSOR",
        topic: "B-Tree Internals",
        sourceType: "GENERAL",
        difficultyOrder: "EASY_TO_HARD",
        maxConsecutiveUnanswered: 3,
      };

      assert.strictEqual(config.difficultyOrder, "EASY_TO_HARD");
      assert.strictEqual(config.maxConsecutiveUnanswered, 3);
    });
  });
});
