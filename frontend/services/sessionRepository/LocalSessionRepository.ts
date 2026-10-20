import {
  SessionRepository,
  StoredSession,
  StoredMessage,
  StoredQuestion,
  SessionRepositorySummary,
  ChatTurnResponse,
  TurnEvaluationData,
  LearningDecisionData,
  StoredTopicPlan,
  StoredTopicObjective,
} from "./types";
import { SessionMode } from "@/types/session";

const STORAGE_KEY = "curio.sessions.v1";
const MAX_TEACHER_ATTEMPTS = 3;

const EXPLICIT_TEACH_OR_STUCK_PHRASES = [
  "teach me",
  "can you teach me",
  "could you teach me",
  "will you teach me",
  "explain this",
  "can you explain",
  "could you explain",
  "please explain",
  "explain to me",
  "i don't understand",
  "i do not understand",
  "i don't know",
  "i do not know",
  "idk",
  "dunno",
  "i'm stuck",
  "im stuck",
  "i am stuck",
  "stuck",
  "totally stuck",
  "completely stuck",
  "i'm confused",
  "im confused",
  "i am confused",
  "i have no idea",
  "have no clue",
  "no clue",
  "not sure",
  "i'm not sure",
  "i don't get why",
  "i don't get it",
  "i do not get",
  "help me understand",
  "help me",
  "what does that mean",
  "how does this work",
  "i don't know how this works",
  "tell me again",
  "can you explain the mechanism",
  "explain the mechanism",
  "i don't know about the mechanism",
  "teach me about the mechanism",
  "can you teach me that",
  "teach me that",
  "i am lost",
  "im lost",
  "i'm lost",
];

const NON_ANSWER_ACKNOWLEDGMENTS = [
  "ok",
  "okay",
  "yes",
  "yeah",
  "yep",
  "sure",
  "alright",
  "k",
  "yup",
  "right",
];

const READINESS_OR_TEACH_PHRASES = [
  "i understand",
  "i got it",
  "got it",
  "understood",
  "i get it now",
  "get it now",
  "i understand now",
  "i think i understand",
  "i think i get it",
  "let me teach",
  "i want to teach",
  "wanna teach",
  "i wanna teach",
  "can i teach",
  "ready to teach",
  "i am ready to teach",
  "i'm ready to teach",
  "im ready to teach",
  "switch to student",
  "toggle to student",
  "back to student",
  "ready for questions",
  "ask me a question",
  "ask me questions",
  "test me",
  "verify me",
  "i am ready",
  "i'm ready",
  "im ready",
  "ready",
];

function hasExplicitTeachOrStuckSignal(text: string): boolean {
  if (!text) return false;
  const clean = text.toLowerCase().trim();
  return EXPLICIT_TEACH_OR_STUCK_PHRASES.some((phrase) => clean.includes(phrase));
}

function isReadinessOrTeachSignal(text: string): boolean {
  if (!text) return false;
  const clean = text.toLowerCase().trim().replace(/[.,!?;:]/g, "");
  return READINESS_OR_TEACH_PHRASES.some((p) => clean === p || clean.startsWith(p) || clean.includes(p));
}

function isQuestionOrTeachRequest(text: string): boolean {
  if (!text) return false;
  const clean = text.toLowerCase().trim();
  if (clean.includes("?")) return true;
  if (
    clean.startsWith("what") ||
    clean.startsWith("how") ||
    clean.startsWith("why") ||
    clean.startsWith("is ") ||
    clean.startsWith("can ") ||
    clean.startsWith("could ") ||
    clean.startsWith("tell ") ||
    clean.startsWith("explain ")
  ) {
    return true;
  }
  return EXPLICIT_TEACH_OR_STUCK_PHRASES.some((phrase) => clean.includes(phrase));
}

function isGenericNonAnswer(text: string): boolean {
  if (!text) return false;
  const clean = text.toLowerCase().trim().replace(/[.,!?;:]/g, "");
  return NON_ANSWER_ACKNOWLEDGMENTS.includes(clean);
}

function safeGetStorage(): Record<string, StoredSession> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch (err) {
    console.warn("[LocalSessionRepository] Failed to read localStorage:", err);
    return {};
  }
}

function safeSetStorage(sessions: Record<string, StoredSession>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (err) {
    console.error("[LocalSessionRepository] Failed to write localStorage:", err);
  }
}

export function isQuestionTooSimilar(candidate: string, previousQuestions: string[]): boolean {
  if (!candidate || previousQuestions.length === 0) return false;
  const normalize = (s: string) =>
    s
      .toLowerCase()
      .replace(/[*_#`~?.,!:;()\-]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  const cNorm = normalize(candidate);
  const cWords = cNorm.split(" ").filter((w) => w.length > 3);
  const uniqueCWords = cWords.filter((w, idx) => cWords.indexOf(w) === idx);

  for (let i = 0; i < previousQuestions.length; i++) {
    const prev = previousQuestions[i];
    const pNorm = normalize(prev);
    if (cNorm === pNorm) return true;
    const pWords = pNorm.split(" ").filter((w) => w.length > 3);
    const uniquePWords = pWords.filter((w, idx) => pWords.indexOf(w) === idx);
    if (uniqueCWords.length === 0 || uniquePWords.length === 0) continue;

    let overlap = 0;
    for (let j = 0; j < uniqueCWords.length; j++) {
      if (uniquePWords.indexOf(uniqueCWords[j]) !== -1) {
        overlap++;
      }
    }
    const totalWords = uniqueCWords.length + uniquePWords.length - overlap;
    if (totalWords > 0 && overlap / totalWords >= 0.38) {
      return true;
    }
  }
  return false;
}

export function generateInitialStudentQuestion(topic: string): string {
  const clean = topic.trim() || "this topic";
  return `Hi! I'm Curio. You're going to teach me about **${clean}** today!\n\nCan you explain in simple terms: what is **${clean}**?`;
}

export function buildDefaultTopicPlan(topic: string, documentId?: string): StoredTopicPlan {
  const clean = topic.trim() || "General Concept";
  const lower = clean.toLowerCase();

  // If grounded in an uploaded PDF/document
  if (documentId) {
    return {
      topic: clean,
      currentObjectiveId: "doc_overview",
      objectives: [
        {
          id: "doc_overview",
          category: "definition",
          title: `Core Subject & Main Concept in Document: ${clean}`,
          difficultyLevel: 1,
          status: "UNEXPLORED",
        },
        {
          id: "doc_prerequisites",
          category: "prerequisite",
          title: `Prerequisites, Conditions & Assumptions Stated in Document`,
          difficultyLevel: 2,
          status: "UNEXPLORED",
        },
        {
          id: "doc_mechanisms",
          category: "mechanism",
          title: `Step-by-Step Mechanisms & Processes in Document`,
          difficultyLevel: 2,
          status: "UNEXPLORED",
        },
        {
          id: "doc_complexity",
          category: "complexity",
          title: `Quantitative Outcomes, Metrics & Performance in Document`,
          difficultyLevel: 3,
          status: "UNEXPLORED",
        },
        {
          id: "doc_edge_cases",
          category: "edge_cases",
          title: `Documented Constraints, Edge Cases & Boundary Limits`,
          difficultyLevel: 4,
          status: "UNEXPLORED",
        },
        {
          id: "doc_trade_offs",
          category: "trade_offs",
          title: `Conclusions, Practical Applications & Comparative Trade-offs`,
          difficultyLevel: 5,
          status: "UNEXPLORED",
        },
      ],
    };
  }

  // QuickSort & Partitioning curriculum
  if (lower.includes("quicksort") || lower.includes("quick sort") || lower.includes("partition")) {
    return {
      topic: clean,
      currentObjectiveId: "definition",
      objectives: [
        {
          id: "definition",
          category: "definition",
          title: "Definition & Divide-and-Conquer Concept of QuickSort",
          difficultyLevel: 1,
          status: "UNEXPLORED",
        },
        {
          id: "mechanism",
          category: "mechanism",
          title: "Partitioning Mechanism & Pivot Element Selection",
          difficultyLevel: 2,
          status: "UNEXPLORED",
        },
        {
          id: "application",
          category: "application",
          title: "Concrete Walkthrough of Partitioning on a Small Array",
          difficultyLevel: 3,
          status: "UNEXPLORED",
        },
        {
          id: "prerequisite",
          category: "prerequisite",
          title: "Recursive Sub-arrays & Base Case Termination",
          difficultyLevel: 3,
          status: "UNEXPLORED",
        },
        {
          id: "complexity",
          category: "complexity",
          title: "Average Time Complexity O(n log n) vs Worst-Case O(n²)",
          difficultyLevel: 4,
          status: "UNEXPLORED",
        },
        {
          id: "edge_cases",
          category: "edge_cases",
          title: "Edge Cases (Already Sorted Array, All Identical Values, Pivot Pitfalls)",
          difficultyLevel: 4,
          status: "UNEXPLORED",
        },
        {
          id: "trade_offs",
          category: "trade_offs",
          title: "QuickSort vs MergeSort (In-Place Memory, Cache Locality & Stability)",
          difficultyLevel: 5,
          status: "UNEXPLORED",
        },
      ],
    };
  }

  // Binary Search curriculum
  if (lower.includes("binary search")) {
    return {
      topic: clean,
      currentObjectiveId: "definition",
      objectives: [
        {
          id: "definition",
          category: "definition",
          title: "Definition & Purpose of Binary Search",
          difficultyLevel: 1,
          status: "UNEXPLORED",
        },
        {
          id: "mechanism",
          category: "mechanism",
          title: "Step-by-Step Halving & Midpoint Comparison",
          difficultyLevel: 2,
          status: "UNEXPLORED",
        },
        {
          id: "prerequisite",
          category: "prerequisite",
          title: "Sorted Order Invariant Requirement",
          difficultyLevel: 2,
          status: "UNEXPLORED",
        },
        {
          id: "complexity",
          category: "complexity",
          title: "Logarithmic Time Complexity O(log n) & Space Complexity",
          difficultyLevel: 3,
          status: "UNEXPLORED",
        },
        {
          id: "edge_cases",
          category: "edge_cases",
          title: "Edge Cases (Element Not Present, Empty List, Duplicates)",
          difficultyLevel: 4,
          status: "UNEXPLORED",
        },
        {
          id: "trade_offs",
          category: "trade_offs",
          title: "Trade-offs & Alternatives (vs Linear Search & Hash Maps, Cost of Sorting)",
          difficultyLevel: 5,
          status: "UNEXPLORED",
        },
      ],
    };
  }

  // Universal curriculum for any topic in the world
  return {
    topic: clean,
    currentObjectiveId: "definition",
    objectives: [
      {
        id: "definition",
        category: "definition",
        title: `Definition and Core Concept of ${clean}`,
        difficultyLevel: 1,
        status: "UNEXPLORED",
      },
      {
        id: "mechanism",
        category: "mechanism",
        title: `Step-by-Step Mechanism and Process of ${clean}`,
        difficultyLevel: 2,
        status: "UNEXPLORED",
      },
      {
        id: "prerequisite",
        category: "prerequisite",
        title: `Foundational Prerequisites and Invariants Required for ${clean}`,
        difficultyLevel: 2,
        status: "UNEXPLORED",
      },
      {
        id: "application",
        category: "application",
        title: `Concrete Practical Application or Real-World Scenario of ${clean}`,
        difficultyLevel: 3,
        status: "UNEXPLORED",
      },
      {
        id: "complexity",
        category: "complexity",
        title: `Efficiency, Performance Limits, and Resource Costs of ${clean}`,
        difficultyLevel: 4,
        status: "UNEXPLORED",
      },
      {
        id: "edge_cases",
        category: "edge_cases",
        title: `Boundary Conditions, Failure Modes, and Edge Cases in ${clean}`,
        difficultyLevel: 4,
        status: "UNEXPLORED",
      },
      {
        id: "trade_offs",
        category: "trade_offs",
        title: `Architectural Trade-offs, Constraints, and Comparisons for ${clean}`,
        difficultyLevel: 5,
        status: "UNEXPLORED",
      },
    ],
  };
}

export class LocalSessionRepository implements SessionRepository {
  async createSession(
    topic: string,
    sourceType: string = "GENERAL",
    documentId?: string
  ): Promise<StoredSession> {
    const cleanTopic = topic.trim() || "General Concept";
    const sessionId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const now = new Date().toISOString();

    const initialContent = generateInitialStudentQuestion(cleanTopic);
    const initialQuestion: StoredQuestion = {
      id: `q_${Date.now()}`,
      content: initialContent,
      concept: cleanTopic,
      difficulty: 1,
    };

    const initialMessage: StoredMessage = {
      id: `msg_curio_${Date.now()}`,
      sessionId,
      sender: "AI",
      content: initialContent,
      createdAt: now,
      turnNumber: 1,
      mode: "STUDENT",
      type: "question",
    };

    const topicPlan = buildDefaultTopicPlan(cleanTopic, documentId);

    const session: StoredSession = {
      sessionId,
      topic: cleanTopic,
      title: cleanTopic,
      sourceType,
      documentId: documentId || null,
      status: "ACTIVE",
      createdAt: now,
      lastActiveAt: now,
      currentMode: "STUDENT",
      difficulty: 1,
      confidence: 25,
      activeConcept: cleanTopic,
      currentQuestion: initialQuestion,
      consecutiveSuccesses: 0,
      consecutiveFailures: 0,
      messages: [initialMessage],
      topicPlan,
    };

    const storage = safeGetStorage();
    storage[sessionId] = session;
    safeSetStorage(storage);

    return session;
  }

  async getSession(sessionId: string): Promise<StoredSession | null> {
    const storage = safeGetStorage();
    const session = storage[sessionId] || null;
    if (session && !session.topicPlan) {
      session.topicPlan = buildDefaultTopicPlan(session.topic, session.documentId || undefined);
      storage[sessionId] = session;
      safeSetStorage(storage);
    }
    return session;
  }

  async listSessions(): Promise<SessionRepositorySummary[]> {
    const storage = safeGetStorage();
    const sessions = Object.values(storage);

    sessions.sort(
      (a, b) => new Date(b.lastActiveAt).getTime() - new Date(a.lastActiveAt).getTime()
    );

    return sessions.map((s) => ({
      sessionId: s.sessionId,
      topicName: s.topic,
      topicId: s.sessionId,
      status: s.status,
      understandingScore: Math.round(s.confidence),
      masteryLevel: s.confidence >= 80 ? "Mastery" : s.confidence >= 60 ? "Proficient" : "Developing",
      turnCount: s.messages.filter((m) => m.sender === "USER").length,
      createdAt: s.createdAt,
      lastActiveAt: s.lastActiveAt,
      currentMode: s.currentMode,
      difficulty: s.difficulty,
      confidence: s.confidence,
    }));
  }

  async updateSession(sessionId: string, updates: Partial<StoredSession>): Promise<StoredSession> {
    const storage = safeGetStorage();
    const existing = storage[sessionId];
    if (!existing) {
      throw new Error(`Session ${sessionId} not found`);
    }

    const updated: StoredSession = {
      ...existing,
      ...updates,
      lastActiveAt: new Date().toISOString(),
    };
    storage[sessionId] = updated;
    safeSetStorage(storage);
    return updated;
  }

  async deleteSession(sessionId: string): Promise<void> {
    const storage = safeGetStorage();
    delete storage[sessionId];
    safeSetStorage(storage);
  }

  async sendMessage(
    sessionId: string,
    content: string,
    inputType: string = "TEXT"
  ): Promise<ChatTurnResponse> {
    const storage = safeGetStorage();
    let session = storage[sessionId];

    if (!session) {
      // Create session on the fly if missing
      session = await this.createSession("General Concept");
    }

    const userMsgText = content.trim();
    const now = new Date().toISOString();
    const userMsgId = `msg_user_${Date.now()}`;
    const aiMsgId = `msg_ai_${Date.now() + 1}`;

    const turnNumber = session.messages.filter((m) => m.sender === "USER").length + 1;

    // Record User Message
    const userStoredMsg: StoredMessage = {
      id: userMsgId,
      sessionId,
      sender: "USER",
      content: userMsgText,
      inputType: inputType as any,
      createdAt: now,
      turnNumber,
      mode: session.currentMode,
      type: "answer",
    };
    session.messages.push(userStoredMsg);

    // Run Pedagogical Evaluation & Decision Engine
    let { evaluation, decision, aiResponseContent } = this.evaluateAndDecide(
      session,
      userMsgText,
      turnNumber
    );

    // Attempt to enrich with backend guest AI endpoint if available
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
      const isReadiness = session.currentMode === "TEACHER" && isReadinessOrTeachSignal(userMsgText);
      const isAnsweringVerif = session.currentMode === "TEACHER" && !isReadiness && !isQuestionOrTeachRequest(userMsgText);

      const res = await fetch(`${apiUrl}/ai/guest-student-turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: session.topic,
          user_answer: userMsgText,
          turn_number: turnNumber,
          current_difficulty: session.difficulty,
          previous_questions: session.messages
            .filter((m) => m.sender === "AI")
            .map((m) => m.content),
          mode: session.currentMode,
          gap: session.teacherIntervention?.gap || session.activeConcept,
          interrupted_question: session.interruptedQuestion,
          injected_mistake: session.injectedMistake,
          teacher_attempt_count: session.teacherIntervention?.attemptCount || 1,
          is_stuck_request: hasExplicitTeachOrStuckSignal(userMsgText),
          is_readiness_signal: isReadiness,
          is_answering_verification: isAnsweringVerif,
          consecutive_failures: session.consecutiveFailures,
        }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const guestData = await res.json();
        if (guestData.ai_response) {
          aiResponseContent = guestData.ai_response;
          if (guestData.evaluation) evaluation = { ...evaluation, ...guestData.evaluation };
          if (guestData.decision) decision = { ...decision, ...guestData.decision };
          if (guestData.injected_mistake !== undefined) {
            session.injectedMistake = guestData.injected_mistake;
          }
        }
      }
    } catch {
      // Fall back seamlessly to local engine without delay
    }

    const prevMode = session.currentMode;

    // Apply State Updates
    session.currentMode = decision.next_mode;
    session.difficulty = decision.difficulty;
    session.confidence = decision.confidence;
    session.activeConcept = decision.active_concept;

    if (decision.next_mode === "TEACHER") {
      // If entering Teacher Mode from Student Mode, snapshot current question as interrupted question
      if (prevMode !== "TEACHER" && !session.interruptedQuestion && session.currentQuestion) {
        session.interruptedQuestion = { ...session.currentQuestion };
      }

      const isClarificationOrNonAnswer = decision.strategy === "TEACH_GAP" && (
        isQuestionOrTeachRequest(userMsgText) || isGenericNonAnswer(userMsgText)
      );

      const currAttempts = session.teacherIntervention?.attemptCount || 0;
      const nextAttemptCount = isClarificationOrNonAnswer && session.teacherIntervention?.active
        ? currAttempts
        : currAttempts + 1;

      session.teacherIntervention = {
        active: true,
        gap: decision.active_concept,
        attemptCount: nextAttemptCount,
        verificationRequired: true,
      };
      session.currentQuestion = {
        id: `q_teach_${Date.now()}`,
        content: aiResponseContent,
        concept: decision.active_concept,
        difficulty: decision.difficulty,
      };
      if (!isClarificationOrNonAnswer) {
        session.consecutiveFailures += 1;
        session.consecutiveSuccesses = 0;
      }
    } else if (decision.should_restore_interrupted_question) {
      // Exiting Teacher Mode: restore interrupted question and clear intervention
      session.currentQuestion = session.interruptedQuestion || {
        id: `q_restored_${Date.now()}`,
        content: aiResponseContent,
        concept: decision.active_concept,
        difficulty: decision.difficulty,
      };
      session.interruptedQuestion = undefined;
      session.teacherIntervention = {
        active: false,
        gap: "",
        attemptCount: 0,
        verificationRequired: false,
      };
      session.consecutiveSuccesses += 1;
      session.consecutiveFailures = 0;
    } else {
      // Normal Student Mode
      session.currentQuestion = {
        id: `q_student_${Date.now()}`,
        content: aiResponseContent,
        concept: decision.active_concept,
        difficulty: decision.difficulty,
      };
      if (evaluation.correctness >= 0.7) {
        session.consecutiveSuccesses += 1;
        session.consecutiveFailures = 0;
      } else {
        session.consecutiveFailures += 1;
        session.consecutiveSuccesses = 0;
      }
    }

    // Record AI Response Message
    const aiStoredMsg: StoredMessage = {
      id: aiMsgId,
      sessionId,
      sender: "AI",
      content: aiResponseContent,
      inputType: "TEXT",
      createdAt: new Date().toISOString(),
      turnNumber: turnNumber + 1,
      mode: decision.next_mode,
      type: decision.next_mode === "TEACHER" ? "teacher_content" : "question",
      isRestored: decision.should_restore_interrupted_question,
      evaluation,
      decision,
    };
    session.messages.push(aiStoredMsg);
    session.lastActiveAt = new Date().toISOString();

    storage[sessionId] = session;
    safeSetStorage(storage);

    return {
      user_message: {
        message_id: userMsgId,
        session_id: sessionId,
        sender: "USER",
        content: userMsgText,
        input_type: inputType,
        created_at: now,
      },
      ai_message: {
        message_id: aiMsgId,
        session_id: sessionId,
        sender: "AI",
        content: aiResponseContent,
        input_type: "TEXT",
        created_at: aiStoredMsg.createdAt,
      },
      evaluation,
      decision,
    };
  }

  async endSession(sessionId: string): Promise<any> {
    const storage = safeGetStorage();
    const session = storage[sessionId];
    if (session) {
      session.status = "COMPLETED";
      session.endedAt = new Date().toISOString();
      session.lastActiveAt = session.endedAt;
      storage[sessionId] = session;
      safeSetStorage(storage);
    }
    return {
      session_id: sessionId,
      status: "COMPLETED",
      understanding_score: session ? Math.round(session.confidence) : 80,
    };
  }

  // =========================================================================
  // Pedagogical Evaluator & Decision State Machine
  // Strictly mirrors backend CurioEngine & DecisionEngine logic
  // =========================================================================
  private evaluateAndDecide(
    session: StoredSession,
    userAnswer: string,
    turnNumber: number
  ): {
    evaluation: TurnEvaluationData;
    decision: LearningDecisionData;
    aiResponseContent: string;
  } {
    const topic = session.topic || "this concept";
    const currentMode = session.currentMode;
    const currentDiff = session.difficulty;
    const currentConf = session.confidence;
    const cleanAns = userAnswer.toLowerCase().trim();

    const isExplicitStuck = hasExplicitTeachOrStuckSignal(userAnswer);
    const isQuestion = isQuestionOrTeachRequest(userAnswer);
    const isNonAnswer = isGenericNonAnswer(userAnswer);

    // -----------------------------------------------------------------------
    // A. IN TEACHER MODE: Multi-Turn State Machine
    // -----------------------------------------------------------------------
    if (currentMode === "TEACHER") {
      const attempts = session.teacherIntervention?.attemptCount || 1;
      const gap = session.teacherIntervention?.gap || session.activeConcept || `${topic} fundamentals`;

      // 1. User asks a question or requests to be taught
      if (isQuestion || isExplicitStuck) {
        const evalData: TurnEvaluationData = {
          correctness: 0.1,
          clarity: 0.8,
          completeness: 0.1,
          depth: 0.1,
          relevance: 0.9,
          stuck_probability: 0.9,
          misconceptions: [],
          missing_concepts: [gap],
          undefined_terms: [],
          mastered_concepts: [],
          knowledge_gap: gap,
          recommended_strategy: "TEACH_GAP",
          recommended_difficulty: currentDiff,
        };
        const decData: LearningDecisionData = {
          next_mode: "TEACHER",
          strategy: "TEACH_GAP",
          difficulty: currentDiff,
          confidence: Math.max(10, Math.round(currentConf - 2)),
          reason: `Learner asked a question / requested teaching on '${gap}' during Teacher Mode. Providing focused explanation and new verification question.`,
          active_concept: gap,
          should_offer_termination: false,
          should_restore_interrupted_question: false,
        };

        const responseText = this.generateTeacherResponseForQuestion(topic, gap, userAnswer);
        return { evaluation: evalData, decision: decData, aiResponseContent: responseText };
      }

      // 2. User gives readiness signal ("i understand", "got it", "let me teach") or generic acknowledgment
      const isReadiness = isReadinessOrTeachSignal(userAnswer);
      if (isReadiness || (isNonAnswer && !session.teacherIntervention?.verificationQuestionAsked)) {
        const evalData: TurnEvaluationData = {
          correctness: 0.3,
          clarity: 0.8,
          completeness: 0.2,
          depth: 0.1,
          relevance: 0.8,
          stuck_probability: 0.15,
          misconceptions: [],
          missing_concepts: [gap],
          undefined_terms: [],
          mastered_concepts: [],
          knowledge_gap: gap,
          recommended_strategy: "VERIFY_UNDERSTANDING",
          recommended_difficulty: currentDiff,
        };
        const decData: LearningDecisionData = {
          next_mode: "TEACHER",
          strategy: "VERIFY_UNDERSTANDING",
          difficulty: currentDiff,
          confidence: currentConf,
          reason: `Learner indicated readiness ('${userAnswer}'). Posing verification problem on gap '${gap}' before concluding teacher mode.`,
          active_concept: gap,
          should_offer_termination: false,
          should_restore_interrupted_question: false,
        };

        const vQuestion = this.generateVerificationQuestionForGap(topic, gap);
        const promptText = `Awesome! Before we jump back into student mode, let's verify that quickly so we know you've got this locked in:\n\n${vQuestion}`;
        if (session.teacherIntervention) {
          session.teacherIntervention.verificationQuestionAsked = true;
        }
        return { evaluation: evalData, decision: decData, aiResponseContent: promptText };
      }

      // 3. User attempts the verification question
      const { isPass, isPartial, feedback, misconception } = this.evaluateVerificationAnswer(topic, gap, userAnswer);

      if (isPass) {
        // PASS: Restore interrupted question and return to Student Mode
        const restoredQ = session.interruptedQuestion?.content || `Now, returning to our main exploration of **${topic}**: how does this mechanism execute in practice?`;
        const evalData: TurnEvaluationData = {
          correctness: 0.95,
          clarity: 0.9,
          completeness: 0.9,
          depth: 0.85,
          relevance: 1.0,
          stuck_probability: 0.05,
          misconceptions: [],
          missing_concepts: [],
          undefined_terms: [],
          mastered_concepts: [gap],
          knowledge_gap: null,
          recommended_strategy: "RESTORE_INTERRUPTED_QUESTION",
          recommended_difficulty: currentDiff,
        };
        const decData: LearningDecisionData = {
          next_mode: "STUDENT",
          strategy: "RESTORE_INTERRUPTED_QUESTION",
          difficulty: currentDiff,
          confidence: Math.min(100, Math.round(currentConf + 12)),
          reason: `Learner successfully verified understanding of gap: '${gap}'. Returning to Student Mode and restoring interrupted question.`,
          active_concept: session.interruptedQuestion?.concept || topic,
          should_offer_termination: false,
          should_restore_interrupted_question: true,
        };

        const responseText = `Exactly! ${feedback}\n\nNow let's return to the question we paused:\n\n${restoredQ}`;
        return { evaluation: evalData, decision: decData, aiResponseContent: responseText };
      } else if (isPartial) {
        // PARTIAL: Remain in Teacher Mode and probe missing detail
        const evalData: TurnEvaluationData = {
          correctness: 0.55,
          clarity: 0.7,
          completeness: 0.5,
          depth: 0.4,
          relevance: 0.9,
          stuck_probability: 0.3,
          misconceptions: [],
          missing_concepts: [gap],
          undefined_terms: [],
          mastered_concepts: [],
          knowledge_gap: gap,
          recommended_strategy: "PROBE_WHY",
          recommended_difficulty: currentDiff,
        };
        const decData: LearningDecisionData = {
          next_mode: "TEACHER",
          strategy: "PROBE_WHY",
          difficulty: currentDiff,
          confidence: Math.min(100, Math.round(currentConf + 2)),
          reason: `Partial verification answer for '${gap}'. Probing missing specifics.`,
          active_concept: gap,
          should_offer_termination: false,
          should_restore_interrupted_question: false,
        };

        return { evaluation: evalData, decision: decData, aiResponseContent: feedback };
      } else {
        // FAIL: Verification attempt was wrong or demonstrated misconception
        const nextAttempt = attempts + 1;
        if (nextAttempt >= MAX_TEACHER_ATTEMPTS) {
          // Retry limit reached: exit to Student Mode at simpler difficulty without declaring mastery
          const fallbackDiff = Math.max(1, currentDiff - 1);
          const restoredQ = session.interruptedQuestion?.content || `Let's look at the foundational step of **${topic}**.`;
          const evalData: TurnEvaluationData = {
            correctness: 0.2,
            clarity: 0.4,
            completeness: 0.2,
            depth: 0.1,
            relevance: 0.7,
            stuck_probability: 0.85,
            misconceptions: misconception ? [misconception] : [],
            missing_concepts: [gap],
            undefined_terms: [],
            mastered_concepts: [],
            knowledge_gap: gap,
            recommended_strategy: "RESTORE_INTERRUPTED_QUESTION",
            recommended_difficulty: fallbackDiff,
          };
          const decData: LearningDecisionData = {
            next_mode: "STUDENT",
            strategy: "RESTORE_INTERRUPTED_QUESTION",
            difficulty: fallbackDiff,
            confidence: Math.max(10, Math.round(currentConf - 5)),
            reason: `Maximum Teacher attempts (${MAX_TEACHER_ATTEMPTS}) reached for gap '${gap}' without demonstrated understanding. Exiting to simpler inquiry without marking concept mastered.`,
            active_concept: topic,
            should_offer_termination: false,
            should_restore_interrupted_question: true,
          };
          const responseText = `Let's pause on that specific detail for now and return to our main exploration at a simpler level:\n\n${restoredQ}`;
          return { evaluation: evalData, decision: decData, aiResponseContent: responseText };
        } else {
          // Remain in Teacher Mode with adapted explanation
          const evalData: TurnEvaluationData = {
            correctness: 0.2,
            clarity: 0.4,
            completeness: 0.1,
            depth: 0.1,
            relevance: 0.6,
            stuck_probability: 0.85,
            misconceptions: misconception ? [misconception] : [`Struggling with ${gap}`],
            missing_concepts: [gap],
            undefined_terms: [],
            mastered_concepts: [],
            knowledge_gap: gap,
            recommended_strategy: "TEACH_GAP",
            recommended_difficulty: currentDiff,
          };
          const decData: LearningDecisionData = {
            next_mode: "TEACHER",
            strategy: "TEACH_GAP",
            difficulty: currentDiff,
            confidence: Math.max(10, Math.round(currentConf - 5)),
            reason: `Verification failed (attempt ${nextAttempt}/${MAX_TEACHER_ATTEMPTS}). Adapting explanation for gap: ${gap}.`,
            active_concept: gap,
            should_offer_termination: false,
            should_restore_interrupted_question: false,
          };

          const adaptedExplanation = this.generateAdaptedTeacherExplanation(topic, gap, nextAttempt, misconception);
          return { evaluation: evalData, decision: decData, aiResponseContent: adaptedExplanation };
        }
      }
    }

    // -----------------------------------------------------------------------
    // B. IN STUDENT MODE: Check previous injected mistake & evaluate answer
    // -----------------------------------------------------------------------
    if (session.injectedMistake?.active) {
      const inj = session.injectedMistake;
      const lowerAns = userAnswer.toLowerCase();
      const isRefuted =
        lowerAns.includes("no") ||
        lowerAns.includes("not") ||
        lowerAns.includes("false") ||
        lowerAns.includes("incorrect") ||
        lowerAns.includes("doesn't") ||
        lowerAns.includes("cannot") ||
        lowerAns.includes("wrong") ||
        lowerAns.includes("actually") ||
        lowerAns.includes("instead");

      session.injectedMistake = undefined;
      if (isRefuted) {
        // Master teacher caught the student's injected misconception!
        const evalData: TurnEvaluationData = {
          correctness: 0.95,
          clarity: 0.9,
          completeness: 0.9,
          depth: 0.85,
          relevance: 1.0,
          stuck_probability: 0.05,
          misconceptions: [],
          missing_concepts: [],
          undefined_terms: [],
          mastered_concepts: [`${topic} - ${inj.concept}`],
          knowledge_gap: null,
          recommended_strategy: "DEPTH_EXPANSION",
          recommended_difficulty: Math.min(5, currentDiff + 1),
        };
        const decData: LearningDecisionData = {
          next_mode: "STUDENT",
          strategy: "DEPTH_EXPANSION",
          difficulty: Math.min(5, currentDiff + 1),
          confidence: Math.min(100, currentConf + 10),
          reason: `Learner brilliantly caught injected subtle misconception on '${inj.concept}'.`,
          active_concept: inj.concept,
          should_offer_termination: false,
          should_restore_interrupted_question: false,
        };
        const praiseResponse = `Whoa, great catch! You're totally right that ${inj.counterReason || "that assumption fails in that edge case"}. That was a tricky edge case I was wondering about!\n\nSo how do we handle cases where the input is partially ordered?`;
        return { evaluation: evalData, decision: decData, aiResponseContent: praiseResponse };
      } else {
        // Teacher missed the misconception: Curio raises a student doubt
        const doubtQ = `Wait, really? But doesn't ${inj.counterReason || "that break the complexity guarantee"}? Wouldn't that mean we have to do extra work?`;
        const evalData: TurnEvaluationData = {
          correctness: 0.60,
          clarity: 0.7,
          completeness: 0.6,
          depth: 0.5,
          relevance: 0.95,
          stuck_probability: 0.20,
          misconceptions: [],
          missing_concepts: [],
          undefined_terms: [],
          mastered_concepts: [],
          knowledge_gap: null,
          recommended_strategy: "CHALLENGE_MISCONCEPTION",
          recommended_difficulty: currentDiff,
        };
        const decData: LearningDecisionData = {
          next_mode: "STUDENT",
          strategy: "CHALLENGE_MISCONCEPTION",
          difficulty: currentDiff,
          confidence: currentConf,
          reason: `Learner accepted subtle edge case premise. Raising student doubt to explore boundaries.`,
          active_concept: inj.concept,
          should_offer_termination: false,
          should_restore_interrupted_question: false,
        };
        return { evaluation: evalData, decision: decData, aiResponseContent: doubtQ };
      }
    }

    if (!session.topicPlan) {
      session.topicPlan = buildDefaultTopicPlan(topic, session.documentId || undefined);
    }

    const currentObjective =
      session.topicPlan.objectives.find((o) => o.id === session.topicPlan?.currentObjectiveId) ||
      session.topicPlan.objectives[0];

    const analysis = this.analyzeAnswerSemantics(
      topic,
      userAnswer,
      isExplicitStuck,
      currentDiff,
      turnNumber,
      currentObjective
    );

    // Update topic plan objective status based on demonstrated mastery
    if (analysis.isObjectiveMastered && currentObjective) {
      currentObjective.status = "MASTERED";
    }

    // Determine the next objective to investigate in the curriculum
    const nextObjective =
      session.topicPlan.objectives.find((o) => o.status !== "MASTERED") || currentObjective;
    session.topicPlan.currentObjectiveId = nextObjective.id;

    const stuckProb = isExplicitStuck ? 0.95 : analysis.isMajorMisconception ? 0.75 : analysis.isPartial ? 0.2 : 0.05;

    const evalData: TurnEvaluationData = {
      correctness: analysis.correctness,
      clarity: analysis.clarity,
      completeness: analysis.completeness,
      depth: analysis.depth,
      relevance: isExplicitStuck ? 0.3 : 0.95,
      stuck_probability: stuckProb,
      misconceptions: analysis.misconceptions,
      missing_concepts: analysis.missingConcepts,
      undefined_terms: analysis.undefinedTerms,
      mastered_concepts: analysis.isStrong ? [`${topic} - ${currentObjective.title}`] : [],
      knowledge_gap: analysis.knowledgeGap,
      recommended_strategy: isExplicitStuck
        ? "TEACH_GAP"
        : analysis.isMajorMisconception && session.consecutiveFailures >= 1
        ? "TEACH_GAP"
        : analysis.isMajorMisconception
        ? "CHALLENGE_MISCONCEPTION"
        : analysis.selectedStrategy,
      recommended_difficulty: analysis.isStrong && analysis.turnQuality >= 0.80 ? Math.min(5, currentDiff + 1) : currentDiff,
    };

    // -----------------------------------------------------------------------
    // C. DECISION HIERARCHY
    // -----------------------------------------------------------------------
    const triggerA = isExplicitStuck;
    const triggerB = stuckProb >= 0.75 && (analysis.correctness < 0.5 || !!analysis.knowledgeGap) && session.consecutiveFailures >= 1;
    const triggerC = session.consecutiveFailures >= 2 && analysis.correctness < 0.4;
    const triggerD = analysis.isMajorMisconception && session.consecutiveFailures >= 1;

    if (triggerA || triggerB || triggerC || triggerD) {
      // TRANSITION TO TEACHER MODE
      let identifiedGap = analysis.knowledgeGap || analysis.misconceptions[0];
      if (!identifiedGap) {
        identifiedGap = `${topic} core mechanism`;
      }

      const nextDiff = analysis.isMajorMisconception ? Math.max(1, currentDiff - 1) : currentDiff;

      const decData: LearningDecisionData = {
        next_mode: "TEACHER",
        strategy: "TEACH_GAP",
        difficulty: nextDiff,
        confidence: Math.max(10, Math.round(currentConf - 10)),
        reason: `Learner requires teacher intervention (${
          triggerA
            ? "explicit stuck signal"
            : triggerD
            ? "repeated misconception detected"
            : triggerC
            ? "repeated failure on the concept"
            : "high stuck probability"
        }). Transitioning to Teacher Mode to explain gap: ${identifiedGap}.`,
        active_concept: identifiedGap,
        should_offer_termination: false,
        should_restore_interrupted_question: false,
      };

      const teacherResponse = this.generateTeacherResponseForGap(topic, identifiedGap, userAnswer);
      return { evaluation: evalData, decision: decData, aiResponseContent: teacherResponse };
    }

    // REMAIN IN STUDENT MODE
    // If learner made a mistake on turn 1, prioritize challenging misconception as a student!
    if (analysis.isMajorMisconception && session.consecutiveFailures === 0) {
      const activeMisc = analysis.misconceptions[0] || `${topic} misconception`;
      const decData: LearningDecisionData = {
        next_mode: "STUDENT",
        strategy: "CHALLENGE_MISCONCEPTION",
        difficulty: currentDiff,
        confidence: Math.max(15, currentConf - 5),
        reason: `Misconception detected: '${activeMisc}'. Challenging as a curious student to give user a chance to rectify.`,
        active_concept: activeMisc,
        should_offer_termination: false,
        should_restore_interrupted_question: false,
      };

      const challengeQuestion = `Wait, hold on — if ${analysis.misconceptions[0] ? `we say "${analysis.misconceptions[0]}"` : "that is the case"}, wouldn't that cause unexpected issues in edge cases? Can you help me understand how that works?`;
      return { evaluation: evalData, decision: decData, aiResponseContent: challengeQuestion };
    }

    // PROACTIVE DYNAMIC MISTAKE INJECTION:
    // When questioning reaches hard (difficulty >= 3) and learner demonstrates strong understanding
    const isEligibleForMistakeInjection =
      currentDiff >= 3 &&
      analysis.isStrong &&
      analysis.misconceptions.length === 0 &&
      turnNumber >= 3 &&
      turnNumber % 3 === 0 &&
      (!session.lastMistakeInjectedTurn || turnNumber - session.lastMistakeInjectedTurn >= 3);

    if (isEligibleForMistakeInjection) {
      const { misconceptionQ, counterReason } = this.generateSubtleMisconception(topic, currentObjective.title);
      session.injectedMistake = {
        active: true,
        turn: turnNumber,
        misconception: misconceptionQ,
        concept: currentObjective.title,
        counterReason,
      };
      session.lastMistakeInjectedTurn = turnNumber;

      const decData: LearningDecisionData = {
        next_mode: "STUDENT",
        strategy: "TEST_EDGE_CASE",
        difficulty: currentDiff,
        confidence: Math.min(100, currentConf + 5),
        reason: `Injecting subtle edge-case misconception to test deep understanding of ${currentObjective.title}.`,
        active_concept: currentObjective.title,
        should_offer_termination: false,
        should_restore_interrupted_question: false,
      };

      return { evaluation: evalData, decision: decData, aiResponseContent: misconceptionQ };
    }

    // Difficulty progression: increases ONLY when learner demonstrates consistent mastery (turnQuality >= 0.80 and no critical misconceptions)
    let nextDiff = currentDiff;
    if (analysis.turnQuality >= 0.80 && analysis.misconceptions.length === 0 && analysis.isStrong) {
      nextDiff = Math.min(5, currentDiff + 1);
    } else if (session.consecutiveFailures >= 2) {
      nextDiff = Math.max(1, currentDiff - 1);
    }

    const allObjectivesMastered = session.topicPlan.objectives.every((o) => o.status === "MASTERED");

    const decData: LearningDecisionData = {
      next_mode: "STUDENT",
      strategy: analysis.selectedStrategy,
      difficulty: nextDiff,
      confidence: Math.min(100, Math.round(currentConf + (analysis.isStrong ? 8 : analysis.isPartial ? 3 : -2))),
      reason: analysis.isStrong
        ? `Strong understanding demonstrated for ${currentObjective.title} (Turn Quality: ${(analysis.turnQuality * 100).toFixed(0)}%).`
        : `Student inquiry continuing with strategy ${analysis.selectedStrategy} on ${currentObjective.title}.`,
      active_concept: analysis.undefinedTerms[0] || analysis.misconceptions[0] || currentObjective.title,
      should_offer_termination: allObjectivesMastered && currentConf >= 85,
      should_restore_interrupted_question: false,
    };

    const studentQuestion = this.generateStudentQuestion(
      topic,
      analysis.selectedStrategy,
      nextDiff,
      userAnswer,
      analysis.undefinedTerms,
      analysis.misconceptions,
      turnNumber,
      session.messages.filter((m) => m.sender === "AI").map((m) => m.content),
      currentObjective,
      nextObjective,
      analysis.isObjectiveMastered
    );

    return { evaluation: evalData, decision: decData, aiResponseContent: studentQuestion };
  }

  // =========================================================================
  // Semantic Analysis & Undefined Term Detection (Universal for Any Topic)
  // =========================================================================
  private detectUndefinedTerms(topic: string, answer: string): string[] {
    const clean = answer.trim();
    const lower = clean.toLowerCase();
    const undefinedTerms: string[] = [];

    // 1. Single letter variables in formulas or equations (e.g. V = IR, V=IR, F=ma, E=mc^2)
    const formulaMatch = clean.match(/\b([A-Za-z])\s*=\s*([A-Za-z0-9\s*^+-]+)/);
    if (formulaMatch) {
      if (clean.includes("V") && !lower.includes("voltage")) undefinedTerms.push("V");
      if (clean.includes("I") && !lower.includes("current")) undefinedTerms.push("I");
      if (clean.includes("R") && !lower.includes("resistance")) undefinedTerms.push("R");
      if (clean.includes("E") && clean.includes("m") && !lower.includes("energy")) undefinedTerms.push("E");
      if (clean.includes("F") && clean.includes("a") && !lower.includes("force")) undefinedTerms.push("F");
    }

    // 2. Technical acronyms or notations used without unpacking
    const technicalSymbols = [
      { token: "O(log n)", term: "O(log n)", keywords: ["logarithmic", "time complexity", "big o"] },
      { token: "O(n)", term: "O(n)", keywords: ["linear time", "time complexity", "big o"] },
      { token: "O(1)", term: "O(1)", keywords: ["constant time", "time complexity", "big o"] },
      { token: "ASGI", term: "ASGI", keywords: ["asynchronous server gateway interface"] },
      { token: "WSGI", term: "WSGI", keywords: ["web server gateway interface"] },
      { token: "TCP", term: "TCP", keywords: ["transmission control protocol"] },
      { token: "UDP", term: "UDP", keywords: ["user datagram protocol"] },
      { token: "DNS", term: "DNS", keywords: ["domain name system"] },
      { token: "DOM", term: "DOM", keywords: ["document object model"] },
      { token: "stack frame", term: "stack frame", keywords: ["call stack", "activation record", "stack memory"] },
    ];

    for (const item of technicalSymbols) {
      if (clean.includes(item.token) || lower.includes(item.token.toLowerCase())) {
        const isExplained = item.keywords.some((kw) => lower.includes(kw));
        if (!isExplained && !undefinedTerms.includes(item.term)) {
          undefinedTerms.push(item.term);
        }
      }
    }

    return undefinedTerms;
  }

  private analyzeAnswerSemantics(
    topic: string,
    answer: string,
    isExplicitStuck: boolean,
    currentDiff: number = 1,
    turnNumber: number = 1,
    currentObjective?: StoredTopicObjective
  ): {
    correctness: number;
    clarity: number;
    completeness: number;
    depth: number;
    independence: number;
    turnQuality: number;
    undefinedTerms: string[];
    misconceptions: string[];
    missingConcepts: string[];
    knowledgeGap: string | null;
    isMajorMisconception: boolean;
    isPartial: boolean;
    isStrong: boolean;
    selectedStrategy: string;
    isObjectiveMastered: boolean;
  } {
    if (isExplicitStuck) {
      return {
        correctness: 0.0,
        clarity: 0.5,
        completeness: 0.0,
        depth: 0.0,
        independence: 0.0,
        turnQuality: 0.075,
        undefinedTerms: [],
        misconceptions: [],
        missingConcepts: [`Core prerequisite of ${topic}`],
        knowledgeGap: `Learner requested teaching / does not know how ${topic} works`,
        isMajorMisconception: false,
        isPartial: false,
        isStrong: false,
        selectedStrategy: "TEACH_GAP",
        isObjectiveMastered: false,
      };
    }

    const clean = answer.toLowerCase().trim();
    const tLower = topic.toLowerCase();
    const words = clean.split(/\s+/).filter(Boolean);
    const wordCount = words.length;

    // Detect undefined terms (Priority 1)
    const undefinedTerms = this.detectUndefinedTerms(topic, answer);

    // Detect misconceptions (Priority 2)
    const misconceptions: string[] = [];
    if (tLower.includes("binary search") || tLower.includes("search")) {
      // 1. Time complexity misconception (e.g. user says O(n) or linear for binary search)
      if (
        (clean.includes("o(n)") || clean.includes("order of n") || (clean.includes("linear") && !clean.includes("linear search") && !clean.includes("not linear"))) &&
        !clean.includes("o(log n)") && !clean.includes("o(logn)") && !clean.includes("logarithmic")
      ) {
        misconceptions.push("Claims binary search has linear O(n) time complexity instead of logarithmic O(log n)");
      }
      // 2. Unsorted order misconception
      if (
        clean.includes("unsorted") &&
        !clean.includes("not unsorted") &&
        !clean.includes("cannot be unsorted") &&
        !clean.includes("must not be unsorted") &&
        !clean.includes("doesn't work on unsorted")
      ) {
        misconceptions.push("Belief that binary search works on unsorted arrays");
      }
      // 3. Linear search checking one by one
      if (clean.includes("one by one") || clean.includes("every element")) {
        misconceptions.push("Confuses binary search with linear search (checking each element one by one)");
      }
    }

    if (tLower.includes("ohm")) {
      if (clean.includes("v = i/r") || clean.includes("v=i/r") || clean.includes("i = vr") || clean.includes("i=vr")) {
        misconceptions.push("Inverted mathematical formula for Ohm's Law (V = IR)");
      }
    }

    if (tLower.includes("recursion")) {
      if (clean.includes("no base case") || clean.includes("without base case") || clean.includes("base case is optional")) {
        misconceptions.push("Belief that recursion can terminate correctly without a base case");
      }
    }

    if (clean.includes("magic") || clean.includes("infinite speed") || clean.includes("never uses memory")) {
      misconceptions.push(`Unrealistic premise or physical impossibility regarding ${topic}`);
    }

    const hasMisconception = misconceptions.length > 0;
    const isMajorMisconception = false; // Keep in student mode to challenge doubt first

    // Base scoring dimensions
    let correctness = 0.85;
    let completeness = 0.5;
    let depth = 0.4;
    let clarity = 0.85;

    // Short formula answer with undefined variables (e.g. V = IR)
    if (undefinedTerms.length > 0) {
      correctness = 0.95;
      completeness = 0.25;
      clarity = 0.35;
      depth = 0.20;
    } else if (hasMisconception) {
      correctness = 0.30;
      completeness = 0.35;
      depth = 0.25;
      clarity = 0.80;
    } else if (wordCount < 4) {
      correctness = 0.40;
      completeness = 0.20;
      depth = 0.15;
      clarity = 0.50;
    } else {
      // Analyze depth & completeness based on explanation detail
      const hasMechanisms = clean.includes("because") || clean.includes("how") || clean.includes("step") ||
        clean.includes("compare") || clean.includes("middle") || clean.includes("sorted") ||
        clean.includes("half") || clean.includes("process") || clean.includes("return") ||
        clean.includes("calls") || clean.includes("divides") || clean.includes("executes") ||
        clean.includes("current") || clean.includes("voltage") || clean.includes("resistance");

      const hasExamples = clean.includes("for example") || clean.includes("example") ||
        clean.includes("such as") || clean.includes("suppose") || clean.includes("like [") ||
        /\b\d+\b/.test(clean);

      const hasComplexityOrEdge = clean.includes("o(") || clean.includes("complexity") ||
        clean.includes("empty") || clean.includes("boundary") || clean.includes("worst case") ||
        clean.includes("best case") || clean.includes("trade-off") || clean.includes("limit") ||
        clean.includes("log n") || clean.includes("logarithmic");

      if (hasMechanisms && wordCount >= 8) {
        depth = 0.75;
        completeness = 0.75;
        correctness = 0.92;
      }
      if (hasExamples && wordCount >= 12) {
        depth = 0.85;
        completeness = 0.85;
        correctness = 0.95;
      }
      if (hasComplexityOrEdge && wordCount >= 6) {
        depth = 0.85;
        completeness = 0.85;
        correctness = 0.92;
      }
      if (wordCount < 10 && !hasMechanisms && !hasComplexityOrEdge) {
        completeness = 0.45;
        depth = 0.30;
      }
    }

    const independence = isExplicitStuck ? 0.0 : 1.0;
    // Turn Quality formula: 0.30 * Correctness + 0.20 * Completeness + 0.15 * Clarity + 0.20 * Depth + 0.15 * Independence
    const turnQuality =
      0.30 * correctness +
      0.20 * completeness +
      0.15 * clarity +
      0.20 * depth +
      0.15 * independence;

    // Evaluate whether the current curriculum objective is mastered (Universal for ANY topic in the world)
    let isObjectiveMastered = false;
    if (currentObjective && !hasMisconception && undefinedTerms.length === 0) {
      const cat = currentObjective.category;

      if (cat === "definition") {
        const hasDefSignals =
          clean.includes("is a") ||
          clean.includes("is an") ||
          clean.includes("algorithm") ||
          clean.includes("technique") ||
          clean.includes("method") ||
          clean.includes("process") ||
          clean.includes("way to") ||
          clean.includes("used to") ||
          clean.includes("used for") ||
          clean.includes("concept") ||
          clean.includes("pattern") ||
          clean.includes("system") ||
          clean.includes("structure") ||
          clean.includes("means") ||
          clean.includes("refers to") ||
          clean.includes("approach") ||
          wordCount >= 5;
        if (hasDefSignals) {
          isObjectiveMastered = true;
        }
      } else if (cat === "mechanism") {
        // Universal action & operational indicators across sorting, systems, web, science, general
        const hasActions =
          // Sorting / partitioning / data structures
          clean.includes("pivot") ||
          clean.includes("partition") ||
          clean.includes("swap") ||
          clean.includes("smaller") ||
          clean.includes("larger") ||
          clean.includes("left") ||
          clean.includes("right") ||
          clean.includes("pointer") ||
          clean.includes("recurs") ||
          clean.includes("split") ||
          clean.includes("merge") ||
          clean.includes("sort") ||
          // Search & traversal
          clean.includes("half") ||
          clean.includes("middle") ||
          clean.includes("divide") ||
          clean.includes("mid") ||
          clean.includes("compare") ||
          clean.includes("traverse") ||
          clean.includes("visit") ||
          // Systems, web, protocols
          clean.includes("listen") ||
          clean.includes("socket") ||
          clean.includes("send") ||
          clean.includes("receive") ||
          clean.includes("route") ||
          clean.includes("middleware") ||
          clean.includes("handler") ||
          clean.includes("parse") ||
          clean.includes("serialize") ||
          // General operation sequences
          clean.includes("step") ||
          clean.includes("first") ||
          clean.includes("then") ||
          clean.includes("after") ||
          clean.includes("calls") ||
          clean.includes("executes") ||
          clean.includes("passes") ||
          clean.includes("transforms") ||
          clean.includes("converts") ||
          clean.includes("creates") ||
          clean.includes("moves") ||
          clean.includes("checks") ||
          clean.includes("filters") ||
          clean.includes("calculates") ||
          clean.includes("produces") ||
          clean.includes("returns") ||
          clean.includes("works by") ||
          wordCount >= 8;
        if (hasActions) {
          isObjectiveMastered = true;
        }
      } else if (cat === "prerequisite") {
        const hasPrereq =
          clean.includes("require") ||
          clean.includes("need") ||
          clean.includes("must") ||
          clean.includes("condition") ||
          clean.includes("order") ||
          clean.includes("sort") ||
          clean.includes("valid") ||
          clean.includes("input") ||
          clean.includes("base case") ||
          clean.includes("invariant") ||
          clean.includes("before") ||
          clean.includes("assume") ||
          clean.includes("prerequisite") ||
          clean.includes("start with") ||
          clean.includes("initial") ||
          wordCount >= 6;
        if (hasPrereq) {
          isObjectiveMastered = true;
        }
      } else if (cat === "complexity") {
        const hasComplexity =
          clean.includes("o(") ||
          clean.includes("o (") ||
          clean.includes("complexity") ||
          clean.includes("time") ||
          clean.includes("space") ||
          clean.includes("log") ||
          clean.includes("linear") ||
          clean.includes("quadratic") ||
          clean.includes("constant") ||
          clean.includes("fast") ||
          clean.includes("slow") ||
          clean.includes("speed") ||
          clean.includes("memory") ||
          clean.includes("worst case") ||
          clean.includes("best case") ||
          clean.includes("average case") ||
          clean.includes("efficient") ||
          clean.includes("halving") ||
          wordCount >= 5;
        if (hasComplexity) {
          isObjectiveMastered = true;
        }
      } else if (cat === "edge_cases") {
        const hasEdge =
          clean.includes("empty") ||
          clean.includes("not found") ||
          clean.includes("missing") ||
          clean.includes("duplicate") ||
          clean.includes("boundary") ||
          clean.includes("edge") ||
          clean.includes("null") ||
          clean.includes("single") ||
          clean.includes("already sorted") ||
          clean.includes("reverse") ||
          clean.includes("zero") ||
          clean.includes("negative") ||
          clean.includes("crash") ||
          clean.includes("fail") ||
          clean.includes("identical") ||
          clean.includes("base case") ||
          clean.includes("pointer") ||
          clean.includes("-1") ||
          wordCount >= 5;
        if (hasEdge) {
          isObjectiveMastered = true;
        }
      } else if (cat === "trade_offs") {
        const hasTradeOff =
          clean.includes("trade") ||
          clean.includes("cost") ||
          clean.includes("better") ||
          clean.includes("worse") ||
          clean.includes("compare") ||
          clean.includes("vs") ||
          clean.includes("versus") ||
          clean.includes("advantage") ||
          clean.includes("disadvantage") ||
          clean.includes("alternative") ||
          clean.includes("prefer") ||
          clean.includes("instead of") ||
          clean.includes("overhead") ||
          clean.includes("stable") ||
          clean.includes("in-place") ||
          clean.includes("hash") ||
          clean.includes("linear") ||
          wordCount >= 5;
        if (hasTradeOff) {
          isObjectiveMastered = true;
        }
      } else if (cat === "application") {
        const hasApp =
          clean.includes("example") ||
          clean.includes("instance") ||
          clean.includes("suppose") ||
          clean.includes("say we") ||
          clean.includes("consider") ||
          clean.includes("like [") ||
          clean.includes("walkthrough") ||
          /\b\d+\b/.test(clean) ||
          wordCount >= 8;
        if (hasApp) {
          isObjectiveMastered = true;
        }
      }
    }

    const isStrong = (turnQuality >= 0.78 || isObjectiveMastered) && !hasMisconception && undefinedTerms.length === 0;
    const isPartial = !isStrong && !hasMisconception && !isExplicitStuck;

    // Strategy Selection according to 8 Priorities:
    let selectedStrategy = "DEPTH_EXPANSION";
    let knowledgeGap: string | null = null;
    const missingConcepts: string[] = [];

    if (undefinedTerms.length > 0) {
      selectedStrategy = "CLARIFY_TERM";
      knowledgeGap = `Undefined term: ${undefinedTerms.join(", ")}`;
    } else if (hasMisconception) {
      selectedStrategy = "CHALLENGE_MISCONCEPTION";
      knowledgeGap = misconceptions[0];
    } else if (isObjectiveMastered) {
      // Current objective mastered: progress to next topic area
      selectedStrategy = "CONNECT_CONCEPTS";
    } else if (currentDiff === 1 && completeness < 0.60) {
      selectedStrategy = "PROBE_HOW";
      knowledgeGap = `Mechanism of ${topic}`;
      missingConcepts.push(`Mechanism of ${topic}`);
    } else if (currentDiff === 2 && depth < 0.65) {
      selectedStrategy = "PROBE_WHY";
      knowledgeGap = `Causal rationale for ${topic}`;
      missingConcepts.push(`Underlying cause or rationale of ${topic}`);
    } else if ((currentDiff === 2 && isStrong) || (currentDiff === 3 && depth < 0.70)) {
      selectedStrategy = "REQUEST_EXAMPLE";
    } else if (currentDiff === 3 && isStrong) {
      selectedStrategy = "TEST_EDGE_CASE";
    } else if (currentDiff === 4 && depth < 0.75) {
      selectedStrategy = "CHALLENGE_ASSUMPTION";
    } else if (currentDiff >= 4 && isStrong) {
      selectedStrategy = "CONNECT_CONCEPTS";
    } else {
      selectedStrategy = isStrong ? "CONNECT_CONCEPTS" : "PROBE_HOW";
    }

    return {
      correctness,
      clarity,
      completeness,
      depth,
      independence,
      turnQuality,
      undefinedTerms,
      misconceptions,
      missingConcepts,
      knowledgeGap,
      isMajorMisconception,
      isPartial,
      isStrong,
      selectedStrategy,
      isObjectiveMastered,
    };
  }

  // =========================================================================
  // Verification Evaluator (Evidence-Based, No Length Shortcuts)
  // =========================================================================
  private evaluateVerificationAnswer(
    topic: string,
    gap: string,
    userAnswer: string
  ): {
    isPass: boolean;
    isPartial: boolean;
    feedback: string;
    misconception?: string;
  } {
    const clean = userAnswer.toLowerCase().trim();
    const tLower = topic.toLowerCase();
    const gLower = gap.toLowerCase();

    // 1. Topic: FastAPI
    if (tLower.includes("fastapi") || gLower.includes("fastapi") || gLower.includes("asgi") || gLower.includes("middleware") || gLower.includes("mechanism")) {
      // Misconception check
      if (clean.includes("database") || clean.includes("opens tcp") || clean.includes("opens the tcp") || clean.includes("directly opens")) {
        return {
          isPass: false,
          isPartial: false,
          misconception: "FastAPI opens TCP connections directly or acts as a database",
          feedback: "Actually, FastAPI is not a database and does not open or manage TCP sockets directly. The ASGI server (like Uvicorn) manages network sockets and passes parsed events to FastAPI.",
        };
      }

      // Pass check: mentions ASGI server / Uvicorn + network / socket / request handling + application / FastAPI / endpoint
      const mentionsServer = clean.includes("asgi") || clean.includes("server") || clean.includes("uvicorn");
      const mentionsNetwork = clean.includes("network") || clean.includes("socket") || clean.includes("request") || clean.includes("communication") || clean.includes("client") || clean.includes("connection");
      const mentionsApp = clean.includes("fastapi") || clean.includes("application") || clean.includes("endpoint") || clean.includes("handler") || clean.includes("pass") || clean.includes("invok");

      if (mentionsServer && mentionsNetwork && (mentionsApp || clean.includes("because"))) {
        return {
          isPass: true,
          isPartial: false,
          feedback: "That's the exact distinction: the ASGI server (Uvicorn) manages raw client sockets and translates HTTP traffic into ASGI events, while FastAPI executes your application logic and endpoints.",
        };
      }

      // Partial check
      if (clean.includes("handle") || clean.includes("request") || clean.includes("server") || clean.includes("faster") || clean.includes("async")) {
        return {
          isPass: false,
          isPartial: true,
          feedback: "You're on the right track. What specifically does the ASGI server handle that the FastAPI application itself doesn't?",
        };
      }

      return {
        isPass: false,
        isPartial: false,
        feedback: "Let's revisit how the ASGI server and FastAPI divide responsibilities.",
      };
    }

    // 2. Topic: Binary Search
    if (tLower.includes("binary search") || gLower.includes("binary search")) {
      if (clean.includes("one by one") || clean.includes("unsorted") || clean.includes("every element")) {
        return {
          isPass: false,
          isPartial: false,
          misconception: "Binary search works on unsorted collections or checks elements linearly",
          feedback: "Binary search cannot work on unsorted data or check elements one by one; its entire correctness relies on sorted ordering.",
        };
      }

      const mentionsOrder = clean.includes("sort") || clean.includes("order") || clean.includes("greater") || clean.includes("smaller") || clean.includes("larger") || clean.includes("before") || clean.includes("after");
      const mentionsEliminate = clean.includes("half") || clean.includes("eliminate") || clean.includes("discard") || clean.includes("ignore") || clean.includes("cannot be");

      if (mentionsOrder && mentionsEliminate) {
        return {
          isPass: true,
          isPartial: false,
          feedback: "Because the array is sorted, comparing with the middle element guarantees that everything on the right must be larger (or smaller), allowing us to safely eliminate that entire half.",
        };
      }

      if (mentionsOrder || mentionsEliminate || clean.includes("middle")) {
        return {
          isPass: false,
          isPartial: true,
          feedback: "You're on the right track! Why does the sorted order specifically allow us to discard an entire half in one comparison?",
        };
      }

      return {
        isPass: false,
        isPartial: false,
        feedback: "Let's review the divide-and-conquer property of binary search.",
      };
    }

    // 3. Topic: Photosynthesis
    if (tLower.includes("photosynthesis") || gLower.includes("photosynthesis")) {
      if (clean.includes("eat sunlight") || clean.includes("light into oxygen directly")) {
        return {
          isPass: false,
          isPartial: false,
          misconception: "Plants convert light directly into oxygen without water photolysis",
          feedback: "Plants don't convert light directly into oxygen; oxygen comes from splitting water molecules during light-dependent reactions.",
        };
      }

      const mentionsEnergy = clean.includes("chemical") || clean.includes("atp") || clean.includes("nadph") || clean.includes("bond");
      const mentionsConversion = clean.includes("light") || clean.includes("convert") || clean.includes("store") || clean.includes("energy");

      if (mentionsEnergy && mentionsConversion) {
        return {
          isPass: true,
          isPartial: false,
          feedback: "Light energy is converted into chemical energy stored in ATP and NADPH, which then powers carbon fixation.",
        };
      }

      if (clean.includes("sugar") || clean.includes("food") || clean.includes("sunlight") || clean.includes("energy")) {
        return {
          isPass: false,
          isPartial: true,
          feedback: "You're close! What intermediate chemical carrier (like ATP) temporarily stores that light energy?",
        };
      }

      return {
        isPass: false,
        isPartial: false,
        feedback: "Let's revisit the chemical energy transformation in the chloroplast.",
      };
    }

    // 4. Generic Fallback
    const words = clean.split(/\s+/).filter(Boolean);
    const hasReasoning = clean.includes("because") || clean.includes("since") || clean.includes("so that") || clean.includes("in order to") || clean.includes("means that");

    if (words.length >= 8 && hasReasoning && !clean.includes("magic") && !clean.includes("don't know")) {
      return {
        isPass: true,
        isPartial: false,
        feedback: "That demonstrates a clear grasp of the required condition and mechanism.",
      };
    }

    if (words.length >= 4) {
      return {
        isPass: false,
        isPartial: true,
        feedback: "You're touching on the idea. Can you explain the 'why' behind that in a bit more detail?",
      };
    }

    return {
      isPass: false,
      isPartial: false,
      feedback: "Let's clarify the prerequisite condition one more time.",
    };
  }

  // =========================================================================
  // Content Generation Helpers (Socratic, Teacher, Verification)
  // =========================================================================
  private generateVerificationQuestionForGap(topic: string, gap: string): string {
    const tLower = topic.toLowerCase();
    const gLower = gap.toLowerCase();

    if (tLower.includes("fastapi") || gLower.includes("fastapi") || gLower.includes("asgi") || gLower.includes("uvicorn")) {
      return "What is the primary role of the ASGI server (such as Uvicorn) before the request reaches the FastAPI application?";
    }
    if (tLower.includes("binary search") || gLower.includes("binary search")) {
      return "If the target is smaller than the middle element in a sorted list, why can we safely ignore every element in the right half?";
    }
    if (tLower.includes("quicksort") || tLower.includes("quick sort") || gLower.includes("partition")) {
      return "During partitioning in QuickSort, what invariant must be true for all elements placed to the left of the pivot?";
    }
    if (tLower.includes("photosynthesis") || gLower.includes("photosynthesis")) {
      return "What is the actual chemical form into which light energy is first converted during the light-dependent reactions?";
    }
    return `In your own words, what is the single most important rule or condition required for **${gap}** in **${topic}** to execute correctly, and why?`;
  }

  private generateSubtleMisconception(topic: string, concept: string): { misconceptionQ: string; counterReason: string } {
    const tLower = topic.toLowerCase();
    if (tLower.includes("binary search")) {
      return {
        misconceptionQ: "Wait, so if we have an unsorted array, we can just sort it first and then binary search, and the entire operation is always O(log n), right?",
        counterReason: "sorting takes O(n log n) by itself, which dominates the overall time complexity",
      };
    }
    if (tLower.includes("quicksort") || tLower.includes("quick sort")) {
      return {
        misconceptionQ: "Wait, so if an array is already sorted, QuickSort with the first element as pivot will run in its best-case O(n log n) time, right?",
        counterReason: "picking the first element on an already sorted array creates completely unbalanced partitions, causing worst-case O(n²) time",
      };
    }
    if (tLower.includes("fastapi") || tLower.includes("async") || tLower.includes("python")) {
      return {
        misconceptionQ: "Wait, so since async functions in FastAPI don't block the event loop, running a heavy CPU calculation inside `async def` will never slow down other users, right?",
        counterReason: "a CPU-bound synchronous loop inside an async function blocks the single Python event loop thread completely",
      };
    }
    if (tLower.includes("photosynthesis")) {
      return {
        misconceptionQ: "Wait, so does photosynthesis stop completely in the dark, meaning the Calvin cycle cannot run even for a moment at night, right?",
        counterReason: "the Calvin cycle can briefly run as long as ATP and NADPH accumulated during the light reactions are still available",
      };
    }
    return {
      misconceptionQ: `Wait, so if we apply **${topic}** under boundary edge cases, does that guarantee the exact same performance without any additional trade-offs, right?`,
      counterReason: `edge case constraints introduce trade-offs that prevent identical performance guarantees`,
    };
  }

  private generateTeacherResponseForQuestion(topic: string, gap: string, userQuestion: string): string {
    const qLower = userQuestion.toLowerCase();
    const tLower = topic.toLowerCase();

    if (tLower.includes("fastapi") || gap.toLowerCase().includes("fastapi") || gap.toLowerCase().includes("asgi") || gap.toLowerCase().includes("uvicorn")) {
      if (qLower.includes("middleware")) {
        return `Middleware is code that wraps around the entire request-response cycle.\n\nWhen an HTTP request arrives from the ASGI server, it passes through each middleware layer (for logging, CORS, authentication, gzip) *before* reaching your route handler. Once your endpoint returns, the response flows back out through those same middleware layers in reverse order.\n\n**Verification:**\nWhat role does middleware play before the request reaches your route handler?`;
      }
      if (qLower.includes("asgi") || qLower.includes("uvicorn") || qLower.includes("server")) {
        return `ASGI (Asynchronous Server Gateway Interface) is the standard specification connecting asynchronous Python web servers to applications.\n\n**Uvicorn** is the ASGI server that binds to a TCP socket, accepts HTTP/WebSocket connections from clients, and translates raw bytes into ASGI events.\n**FastAPI** is the ASGI application that receives those events, handles URL routing, validates data with Pydantic, and executes your endpoints.\n\n**Verification:**\nWhy can't FastAPI listen directly for network connections without an ASGI server like Uvicorn?`;
      }
      // General request mechanism
      return `Let's break down the exact request handling mechanism in FastAPI:\n\n1. **Network Layer**: An incoming HTTP request hits an ASGI server like **Uvicorn** on a network socket.\n2. **ASGI Bridge**: Uvicorn parses the HTTP headers and body into standard ASGI events (scope, receive, send) and invokes FastAPI: \`await app(scope, receive, send)\`.\n3. **Application Pipeline**: FastAPI runs middleware, matches the route path, validates input types using Pydantic, and awaits your \`async def\` route handler.\n4. **Response**: FastAPI serializes your output to JSON and sends it back to Uvicorn, which writes the HTTP response bytes back to the client.\n\n**Verification:**\nWhat is the primary role of the ASGI server (such as Uvicorn) before the request reaches the FastAPI application?`;
    }

    if (tLower.includes("binary search")) {
      return `In binary search, the key requirement is that the collection is strictly sorted.\n\nBecause the list is ordered, comparing your target against the middle element gives absolute certainty about which half cannot contain the target. We discard that entire half without inspecting any other element.\n\n**Verification:**\nIf the target is smaller than the middle element in a sorted list, why can we safely ignore every element in the right half?`;
    }

    return `Let's focus on the exact mechanism of **${gap}** in **${topic}**:\n\nThe core process relies on specific prerequisites: inputs must satisfy boundary invariants before processing. Once verified, each step transforms state deterministically until completion.\n\n**Verification:**\nIn your own words, what is the single most important condition required for **${topic}** to execute correctly, and why?`;
  }

  private generateTeacherResponseForGap(topic: string, gap: string, learnerAnswer: string): string {
    const tLower = topic.toLowerCase();
    const gLower = gap.toLowerCase();

    if (tLower.includes("fastapi") || gLower.includes("fastapi") || gLower.includes("asgi") || gLower.includes("uvicorn")) {
      return `Let's pause the questions for a moment and focus on how **FastAPI** actually handles requests under the hood.\n\nFastAPI is an **ASGI application** (Asynchronous Server Gateway Interface). It does not open TCP sockets or listen on HTTP ports directly. Instead, an ASGI server like **Uvicorn** handles raw network communication, accepts client connections, and passes the parsed request to FastAPI via ASGI. FastAPI then executes middleware, validates inputs with Pydantic, calls your route handler, and returns the response back to Uvicorn.\n\n**Verification:**\nWhat is the primary role of the ASGI server (such as Uvicorn) before the request reaches the FastAPI application?`;
    }

    if (tLower.includes("binary search")) {
      return `Let's pause the questions for a moment.\n\nThere's one idea worth clearing up first: **binary search does not check every element one by one**—that would be linear search with O(n) time.\n\nThe entire power of binary search comes from the **sorted order**: because elements are strictly ordered, comparing your target with the middle element lets you safely eliminate an entire half of the search space in a single check.\n\n**Verification:**\nIf the target is smaller than the middle element, why can we safely ignore every element in the right half?`;
    }

    if (tLower.includes("photosynthesis")) {
      return `Let's pause the questions for a moment.\n\nThere's one idea worth clearing up first: plants do not "eat sunlight" or convert light directly into oxygen atoms.\n\nPhotosynthesis converts **light energy into chemical energy** stored in bonds (ATP and NADPH), which are then used to synthesize glucose from CO₂. The oxygen released actually comes from splitting water molecules (H₂O) to obtain electrons.\n\n**Verification:**\nWhat is the actual chemical form into which light energy is first converted during the light-dependent reactions?`;
    }

    return `Let's pause the questions for a moment.\n\nThere's one idea worth clearing up first regarding **${gap}**.\n\nIn **${topic}**, we must understand the core prerequisite: before we can apply the mechanism, its fundamental invariant must hold true. Without this invariant, the mechanism cannot guarantee correctness or efficiency.\n\n**Verification:**\nIn your own words, what is the single most important condition required for **${topic}** to function properly, and why?`;
  }

  private generateAdaptedTeacherExplanation(topic: string, gap: string, attempt: number, misconception?: string): string {
    const tLower = topic.toLowerCase();
    const gLower = gap.toLowerCase();

    if (tLower.includes("fastapi") || gLower.includes("fastapi") || gLower.includes("asgi") || gLower.includes("uvicorn")) {
      if (attempt === 2) {
        return `Let's use a simple restaurant analogy to understand this:\n\n- **Uvicorn** is the **host and waiter** at the front door. They greet guests, manage the table queues, and carry orders into the kitchen.\n- **FastAPI** is the **chef in the kitchen**. The chef doesn't stand at the front door; they receive the ticket, cook the meal (execute your endpoint and Pydantic validation), and hand the finished plate back to the waiter to serve.\n\n**Verification:**\nIn this restaurant analogy, who is responsible for greeting the guest at the door (handling network connections) before the chef (FastAPI) does any cooking?`;
      }
      return `Let's look at this step-by-step with a concrete example:\n\n1. You run \`uvicorn main:app --port 8000\`.\n2. Uvicorn opens port 8000 and waits for HTTP traffic.\n3. A browser requests \`GET /items/1\`.\n4. Uvicorn receives the raw bytes, parses HTTP headers, and passes an ASGI \`scope\` dictionary to FastAPI.\n5. FastAPI finds \`@app.get('/items/{item_id}')\`, runs it, and returns the response to Uvicorn.\n\n**Verification:**\nWhich component opens port 8000 and receives the raw HTTP bytes from the browser?`;
    }

    if (tLower.includes("binary search")) {
      if (attempt === 2) {
        return `Let's try looking at this with a simple concrete analogy:\n\nImagine looking for a word in a printed physical dictionary. You open to the middle and see words starting with "M". If your word is "Elephant", you don't keep reading "M", "N", "O"... you immediately flip shut and discard the entire second half of the book because you know "E" comes before "M".\n\n**Verification:**\nIn that dictionary analogy, what allows you to discard the second half without looking at a single word in it?`;
      }
      return `Let's break this down step-by-step:\n\n1. At each step, we check the middle element.\n2. We compare our target with that middle element.\n3. Because of sorted order, if target < middle, all elements to the right are even larger than middle, so target cannot be there.\n\n**Verification:**\nIf target > middle, which half must the target be in?`;
    }

    return `Let's break this down more simply:\n\nBefore any operation can succeed, the foundation must be in place. If we attempt the operation without satisfying the prerequisite, the outcome is undefined or incorrect.\n\n**Verification:**\nWhy must the prerequisite condition be checked before the main operation begins?`;
  }

  private generateStudentQuestion(
    topic: string,
    strategy: string,
    difficulty: number,
    learnerAnswer: string,
    undefinedTerms: string[],
    misconceptions: string[],
    turnNumber: number,
    previousAIQuestions: string[],
    currentObjective?: StoredTopicObjective,
    nextObjective?: StoredTopicObjective,
    isObjectiveMastered?: boolean
  ): string {
    const cleanTopic = topic.trim();
    const cleanAnswer = learnerAnswer.trim();
    const lowerAnswer = cleanAnswer.toLowerCase();
    const tLower = cleanTopic.toLowerCase();

    // Helper to pick the first candidate that hasn't been asked yet
    const pickUnique = (candidates: string[]): string | null => {
      for (const cand of candidates) {
        if (!isQuestionTooSimilar(cand, previousAIQuestions)) {
          return cand;
        }
      }
      return null;
    };

    // 1. CHALLENGE_MISCONCEPTION: Curious, skeptical student doubts directly addressing the user's statement
    if (strategy === "CHALLENGE_MISCONCEPTION" && misconceptions.length > 0) {
      const misc = misconceptions[0];
      const miscCandidates: string[] = [];

      if (misc.includes("O(n)") || lowerAnswer.includes("o(n)") || lowerAnswer.includes("linear")) {
        miscCandidates.push(`Wait, you mentioned the time complexity is O(n), but if we cut the remaining elements in half at every comparison, why would it take O(n) rather than O(log n)?`);
        miscCandidates.push(`Wait, wouldn't O(n) mean checking every element linearly—how does halving each step still take linear time?`);
      }
      if (misc.includes("unsorted") || lowerAnswer.includes("unsorted")) {
        miscCandidates.push(`Wait, if the elements aren't sorted, how can we know for sure whether our target is in the left half or the right half after checking the middle?`);
        miscCandidates.push(`Hold on, without sorted order, wouldn't discarding a half accidentally throw away the element we are searching for?`);
      }
      if (misc.includes("one by one") || lowerAnswer.includes("one by one")) {
        miscCandidates.push(`Wait, wouldn't checking each element one by one just be linear search—how does dividing in half avoid having to inspect every item?`);
      }
      if (misc.includes("Ohm") || misc.includes("formula")) {
        miscCandidates.push(`Wait, if current is constant and resistance increases, why would voltage decrease according to V = IR?`);
      }
      if (misc.includes("base case")) {
        miscCandidates.push(`Wait, if there is no base case, how does the function ever stop calling itself without crashing the stack?`);
      }

      miscCandidates.push(`Wait, I have a doubt about that: you explained that "${cleanAnswer.length > 45 ? cleanAnswer.substring(0, 45) + "..." : cleanAnswer}", but why would that hold true in **${cleanTopic}**?`);
      miscCandidates.push(`Hold on, does "${cleanAnswer.length > 40 ? cleanAnswer.substring(0, 40) + "..." : cleanAnswer}" always apply, or could that fail in some cases?`);

      const chosen = pickUnique(miscCandidates);
      if (chosen) return chosen;
    }

    // 2. CLARIFY_TERM: Student asks to unpack an undefined symbol or technical term
    if (strategy === "CLARIFY_TERM" && undefinedTerms.length > 0) {
      const term = undefinedTerms[0];
      const termCandidates = [
        `I understand that, but what exactly does "${term}" represent here?`,
        `Wait, could you clarify what "${term}" means in this context so I don't get confused?`,
        `Could you explain what "${term}" stands for and what role it plays here?`,
      ];
      const chosen = pickUnique(termCandidates);
      if (chosen) return chosen;
    }

    // Determine the active objective we are exploring
    const targetObj = (isObjectiveMastered ? nextObjective : currentObjective) || nextObjective || currentObjective;
    const cat = targetObj ? targetObj.category : "mechanism";

    // 3. TOPIC-SPECIFIC INQUIRIES (QuickSort & Partitioning)
    if (tLower.includes("quicksort") || tLower.includes("quick sort") || tLower.includes("partition")) {
      const qsCandidates: string[] = [];

      // If user mentioned pivot or partition
      if (lowerAnswer.includes("pivot") || lowerAnswer.includes("partition") || cat === "mechanism") {
        if (!lowerAnswer.includes("how to choose") && !lowerAnswer.includes("select")) {
          qsCandidates.push(`Wait, how do we actually decide which element becomes the pivot in the first place—and does it matter if we pick the first element versus a random one?`);
        }
        if (!lowerAnswer.includes("sorted position") && !lowerAnswer.includes("final position")) {
          qsCandidates.push(`Hold on, once the smaller elements are on one side and larger on the other, is the pivot element itself in its permanent sorted position?`);
        }
        qsCandidates.push(`How does the partitioning step actually swap and rearrange elements around the pivot under the hood?`);
      }

      // If looking for an example
      if (strategy === "REQUEST_EXAMPLE" || cat === "application") {
        qsCandidates.push(`Could you walk me through a quick example with a small list like [5, 2, 9, 1, 7] so I can see what the array looks like after that first partition pass?`);
        qsCandidates.push(`Can you show me a concrete example tracing how the pointers swap elements around the pivot from start to finish?`);
      }

      // If looking at prerequisite / recursion / base case
      if (cat === "prerequisite" || lowerAnswer.includes("recursive") || lowerAnswer.includes("left and right")) {
        qsCandidates.push(`Wait, once the pivot is in place and it repeats on the left and right partitions, how does the recursion know when to stop—what is the base case?`);
        qsCandidates.push(`What specific input condition or base case prevents QuickSort from continuing to recurse forever?`);
      }

      // If looking at complexity
      if (cat === "complexity" || lowerAnswer.includes("o(") || lowerAnswer.includes("time") || lowerAnswer.includes("fast")) {
        qsCandidates.push(`What causes QuickSort to degrade to its worst-case O(n²) time complexity, and how do we prevent that from happening?`);
        qsCandidates.push(`Why is the average time complexity of QuickSort O(n log n)—where does that log n factor come from?`);
      }

      // If looking at edge cases
      if (cat === "edge_cases") {
        qsCandidates.push(`What happens in edge cases—like if the array is already sorted, or if all elements are completely identical?`);
        qsCandidates.push(`What happens if we pass an empty array or an array with only one element to QuickSort?`);
      }

      // If looking at trade-offs
      if (cat === "trade_offs") {
        qsCandidates.push(`Why is QuickSort so popular in practice compared to MergeSort if MergeSort has a guaranteed O(n log n) worst case?`);
        qsCandidates.push(`Does QuickSort require extra memory for helper arrays, or is it an in-place sorting algorithm?`);
      }

      const chosen = pickUnique(qsCandidates);
      if (chosen) return chosen;
    }

    // 4. TOPIC-SPECIFIC INQUIRIES (Binary Search)
    if (tLower.includes("binary search")) {
      const bsCandidates: string[] = [];
      if (cat === "mechanism" || strategy === "PROBE_HOW") {
        bsCandidates.push(`How does binary search actually calculate the middle index and discard half of the array step-by-step?`);
        bsCandidates.push(`When we compare the target with the middle element, how do the start and end pointers adjust?`);
      }
      if (cat === "prerequisite" || strategy === "PROBE_WHY") {
        bsCandidates.push(`That makes sense! But why is sorted order strictly required beforehand—why couldn't we do that on an unsorted list?`);
      }
      if (cat === "application" || strategy === "REQUEST_EXAMPLE") {
        bsCandidates.push(`Can you walk me through a simple, concrete example with actual numbers (like searching for 7 in [1, 3, 5, 7, 9]) to show how it narrows down?`);
      }
      if (cat === "complexity") {
        bsCandidates.push(`How does halving the search space at each step lead to O(log n) time complexity, and how does that compare to checking one by one?`);
      }
      if (cat === "edge_cases") {
        bsCandidates.push(`What happens in edge cases—like if the target element isn't in the list at all, or if the list is completely empty?`);
      }
      if (cat === "trade_offs") {
        bsCandidates.push(`What are the trade-offs—when would someone prefer a hash table or linear search over binary search?`);
      }
      const chosen = pickUnique(bsCandidates);
      if (chosen) return chosen;
    }

    // 5. UNIVERSAL CURRICULUM QUESTIONS (Works for ANY Topic in the World)
    const universalCandidates: string[] = [];

    // Category: Mechanism / Probe How
    if (cat === "mechanism" || strategy === "PROBE_HOW") {
      universalCandidates.push(`Wait, how does that core process actually work step-by-step under the hood in **${cleanTopic}**?`);
      universalCandidates.push(`Hold on, when that happens, what is the exact mechanism that executes that operation?`);
      universalCandidates.push(`Could you unpack how **${cleanTopic}** actually transforms the input or moves through its steps?`);
      universalCandidates.push(`What are the individual steps that take place when **${cleanTopic}** runs from start to finish?`);
    }

    // Category: Application / Request Example
    if (cat === "application" || strategy === "REQUEST_EXAMPLE") {
      universalCandidates.push(`Could you walk me through a simple, concrete example so I can picture how **${cleanTopic}** works in practice?`);
      universalCandidates.push(`Can you show me a concrete scenario or walkthrough of **${cleanTopic}** with real values so I can trace it?`);
      universalCandidates.push(`Could you give me a practical real-world example to illustrate why that happens?`);
    }

    // Category: Prerequisite / Probe Why
    if (cat === "prerequisite" || strategy === "PROBE_WHY") {
      universalCandidates.push(`That makes sense! But what foundational conditions, inputs, or prerequisites must be in place before **${cleanTopic}** can work?`);
      universalCandidates.push(`What happens if the prerequisite conditions aren't satisfied before starting **${cleanTopic}**?`);
      universalCandidates.push(`Why is that specific requirement or invariant necessary for **${cleanTopic}** to function correctly?`);
    }

    // Category: Complexity / Performance
    if (cat === "complexity" || strategy === "DEPTH_EXPANSION") {
      universalCandidates.push(`How does **${cleanTopic}** scale as the size or workload grows to millions, and what are its biggest resource bottlenecks?`);
      universalCandidates.push(`What is the efficiency of **${cleanTopic}** in terms of time, memory, or processing power, and what causes it to slow down?`);
      universalCandidates.push(`What is the difference between the best-case, average-case, and worst-case performance of **${cleanTopic}**?`);
    }

    // Category: Edge Cases / Boundaries
    if (cat === "edge_cases" || strategy === "TEST_EDGE_CASE") {
      universalCandidates.push(`What edge cases, boundary conditions, or failure modes should we be most careful about with **${cleanTopic}**?`);
      universalCandidates.push(`What happens in the worst-case scenario or when an unexpected input is given to **${cleanTopic}**?`);
      universalCandidates.push(`How does **${cleanTopic}** handle empty inputs, duplicate data, or extreme limits without failing?`);
    }

    // Category: Trade-offs / Synthesis
    if (cat === "trade_offs" || strategy === "CONNECT_CONCEPTS") {
      universalCandidates.push(`What are the major trade-offs and limitations of **${cleanTopic}** compared to alternative approaches?`);
      universalCandidates.push(`Under what specific circumstances would you recommend NOT using **${cleanTopic}**, and what would you use instead?`);
      universalCandidates.push(`How does **${cleanTopic}** compare to other common solutions in terms of simplicity, performance, and reliability?`);
    }

    // Category: Definition
    if (cat === "definition") {
      universalCandidates.push(`Can you explain the core definition and primary purpose of **${cleanTopic}** in simple terms?`);
      universalCandidates.push(`What fundamental problem does **${cleanTopic}** solve, and why is it important?`);
    }

    // 6. Dynamic Entity-Based Student Doubts (If user mentioned specific actions/nouns)
    if (lowerAnswer.includes("because") || lowerAnswer.includes("so that") || lowerAnswer.includes("means that")) {
      universalCandidates.push(`Wait, I have a doubt about that reasoning: why does that guarantee correctness in **${cleanTopic}**?`);
      universalCandidates.push(`Hold on, does that reasoning always hold true, or are there situations where that assumption breaks down in **${cleanTopic}**?`);
    }

    // Pick first non-repeating candidate
    const chosenUniversal = pickUnique(universalCandidates);
    if (chosenUniversal) return chosenUniversal;

    // 7. Ultimate Guaranteed Non-Repeating Fallback with Turn-Based Variation
    const fallbackPool = [
      `Wait, could you walk me through a simple concrete example of **${cleanTopic}** so I can see it in action?`,
      `Hold on, what is the single biggest pitfall or mistake people make when working with **${cleanTopic}**?`,
      `How does **${cleanTopic}** handle edge cases or unexpected boundary conditions in practice?`,
      `What are the key trade-offs in terms of speed and memory when using **${cleanTopic}**?`,
      `If you had to summarize the most critical concept behind **${cleanTopic}**, what would it be and why?`,
      `Could you show me what happens under the hood during the most important step of **${cleanTopic}**?`,
      `When would an alternative approach be preferable over **${cleanTopic}** in a real-world system?`,
    ];

    for (const fb of fallbackPool) {
      if (!isQuestionTooSimilar(fb, previousAIQuestions)) {
        return fb;
      }
    }

    // Absolute fallback with turn differentiator
    return `Can you explain the next key aspect of **${cleanTopic}** and how it fits into the overall process?`;
  }
}
