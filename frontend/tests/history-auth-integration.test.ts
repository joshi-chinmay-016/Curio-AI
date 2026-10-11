import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { ApiSessionRepository } from "../services/sessionRepository/ApiSessionRepository";
import {
  getSessions,
  evaluateSession,
  getGapReport,
  regenerateReport,
} from "../services/gapReportService";
import {
  formatConfidenceScore,
  DEFAULT_CONFIDENCE,
  getSessionHistory,
} from "../services/historyService";

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

describe("Authenticated History and Session Integration Regression Tests", () => {
  const originalFetch = globalThis.fetch;
  let recordedRequests: Array<{ url: string; options: RequestInit }> = [];

  beforeEach(() => {
    mockStorage.clear();
    recordedRequests = [];
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  // 1. Session requests use the authenticated API client
  test("1. Session requests use the authenticated API client with bearer token", async () => {
    mockStorage.setItem("curio_access_token", "test-auth-token-123");

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      recordedRequests.push({ url: String(input), options: init || {} });
      const headers = (init?.headers || {}) as Record<string, string>;
      assert.equal(headers["Authorization"], "Bearer test-auth-token-123");

      return new Response(
        JSON.stringify({
          session_id: "sess_456",
          topic: "Binary Search",
          status: "ACTIVE",
          current_mode: "STUDENT",
          difficulty: 1,
          confidence: 0.8,
          created_at: new Date().toISOString(),
          last_active_at: new Date().toISOString(),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    };

    const repo = new ApiSessionRepository();
    const session = await repo.createSession("Binary Search");

    assert.ok(session);
    assert.equal(session.sessionId, "sess_456");
    assert.equal(session.topic, "Binary Search");
    assert.equal(recordedRequests.length, 1);
    assert.match(recordedRequests[0].url, /\/sessions$/);
  });

  // 2. Session request errors propagate correctly
  test("2. Session request errors propagate correctly on 401 unauthorized", async () => {
    mockStorage.setItem("curio_access_token", "expired-token");

    globalThis.fetch = async () => {
      return new Response(
        JSON.stringify({ detail: "Could not validate credentials" }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      );
    };

    const repo = new ApiSessionRepository();
    await assert.rejects(
      async () => {
        await repo.createSession("Failing Session");
      },
      (err: any) => {
        assert.equal(err.status, 401);
        assert.match(err.message, /unauthorized/i);
        return true;
      }
    );
  });

  test("2b. Session getSession returns null on 404 not found cleanly", async () => {
    mockStorage.setItem("curio_access_token", "valid-token");

    globalThis.fetch = async () => {
      return new Response(
        JSON.stringify({ detail: "Session not found" }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    };

    const repo = new ApiSessionRepository();
    const result = await repo.getSession("non-existent-session");
    assert.equal(result, null);
  });

  // 3. Gap-report requests use the authenticated API client
  test("3. Gap-report requests use the authenticated API client with bearer token", async () => {
    mockStorage.setItem("curio_access_token", "valid-user-token");

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      recordedRequests.push({ url, options: init || {} });
      const headers = (init?.headers || {}) as Record<string, string>;
      assert.equal(headers["Authorization"], "Bearer valid-user-token");

      if (url.endsWith("/sessions")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                session_id: "sess_rep_1",
                topic: "Recursion",
                status: "COMPLETED",
                created_at: new Date().toISOString(),
                last_active_at: new Date().toISOString(),
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      if (url.includes("/report")) {
        return new Response(
          JSON.stringify({
            session_id: "sess_rep_1",
            understanding_score: 85,
            mastery_level: "PROFICIENT",
            evidence_confidence: 0.9,
            strengths: ["Base cases"],
            concept_assessments: [],
            high_priority_learning_gaps: [],
            medium_priority_learning_gaps: [],
            low_priority_learning_gaps: [],
            misconceptions_detected: [],
            concepts_mastered: [],
            teacher_interventions_required: 0,
            difficulty_achieved: 1,
            personalized_roadmap: [],
            recommended_exercises: [],
            resolved_gaps: [],
            unresolved_gaps: [],
            resolved_misconceptions: [],
            unresolved_misconceptions: [],
            created_at: new Date().toISOString(),
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      return new Response("Not found", { status: 404 });
    };

    const report = await getGapReport("sess_rep_1");
    assert.ok(report);
    assert.equal(report?.sessionId, "sess_rep_1");
    assert.ok(recordedRequests.some((r) => r.url.includes("/report")));
  });

  // 4. Unauthorized report requests do not return mock data as though it were real
  test("4. Unauthorized report requests throw and do NOT return mock data as real", async () => {
    mockStorage.setItem("curio_access_token", "invalid-or-expired-token");

    globalThis.fetch = async () => {
      return new Response(
        JSON.stringify({ detail: "Invalid token or signature" }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      );
    };

    await assert.rejects(
      async () => {
        await getGapReport("session_abc");
      },
      (err: any) => {
        assert.equal(err.status, 401);
        return true;
      }
    );
  });

  // 5. Legitimate offline/demo fallback remains functional where intended
  test("5. Legitimate demo mode returns mock report for demo token", async () => {
    mockStorage.setItem("curio_access_token", "demo-session-token");

    let fetchCalled = false;
    globalThis.fetch = async () => {
      fetchCalled = true;
      return new Response("{}", { status: 200 });
    };

    const demoReport = await getGapReport("demo_session");
    assert.ok(demoReport);
    assert.equal(demoReport?.sessionId, "demo_session");
    assert.equal(fetchCalled, false, "Demo token should bypass network calls and return mock data directly");
  });

  test("5b. Offline visitor without token returns mock report fallback on network failure", async () => {
    // No token in storage (visitor)
    globalThis.fetch = async () => {
      throw new Error("Network unreachable");
    };

    const fallbackReport = await getGapReport("offline_session");
    assert.ok(fallbackReport);
    assert.equal(fallbackReport?.sessionId, "offline_session");
  });

  // 6. Confidence 0.8 displays as 80%, not 1%
  test("6. Confidence 0.8 displays as 80% and not 1%", () => {
    const formatted = formatConfidenceScore(0.8);
    assert.equal(formatted, 80);
    assert.notEqual(formatted, 1);
  });

  // 7. Null confidence uses the established fallback
  test("7. Null confidence uses established default fallback (60%)", () => {
    const nullScore = formatConfidenceScore(null);
    assert.equal(nullScore, 60);

    const undefinedScore = formatConfidenceScore(undefined);
    assert.equal(undefinedScore, 60);

    const zeroScore = formatConfidenceScore(0);
    assert.equal(zeroScore, 0, "Zero confidence must be preserved as 0%, not default");
  });

  // 8. Missing turn counts or duration are not fabricated
  test("8. Missing turn counts or duration are not fabricated in getSessionHistory", async () => {
    mockStorage.setItem("curio_access_token", "user-token");

    const startTime = "2024-01-01T10:00:00.000Z";
    const endTime = "2024-01-01T10:15:00.000Z"; // 15 mins later

    globalThis.fetch = async () => {
      return new Response(
        JSON.stringify({
          items: [
            {
              session_id: "sess_honest",
              topic: "Dynamic Programming",
              status: "COMPLETED",
              current_mode: "STUDENT",
              difficulty: 3, // In old code, this fabricated turnCount=9 and duration=21
              confidence: 0.8,
              created_at: startTime,
              last_active_at: endTime,
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
          pages: 1,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    };

    const history = await getSessionHistory();
    assert.equal(history.length, 1);
    const item = history[0];

    assert.equal(item.understandingScore, 80);
    // Not fabricated turn count (was difficulty * 3 = 9)
    assert.equal(item.turnCount, 0);
    // Real duration calculated from timestamps (15 minutes), not fabricated (difficulty * 7 = 21)
    assert.equal(item.durationMinutes, 15);
  });
});
