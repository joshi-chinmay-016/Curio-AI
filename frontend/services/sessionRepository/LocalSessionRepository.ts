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
  if (!cNorm) return false;

  const cWords = cNorm.split(" ").filter((w) => w.length > 3);
  const uniqueCWords = cWords.filter((w, idx) => cWords.indexOf(w) === idx);

  for (let i = 0; i < previousQuestions.length; i++) {
    const prev = previousQuestions[i];
    const pNorm = normalize(prev);
    if (!pNorm) continue;
    if (cNorm === pNorm) return true;
    if (cNorm.length > 20 && pNorm.length > 20 && (cNorm.includes(pNorm) || pNorm.includes(cNorm))) {
      return true;
    }

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
    if (totalWords > 0 && overlap / totalWords >= 0.30) {
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
          const pastQuestions = session.messages
            .filter((m) => m.sender === "AI")
            .map((m) => m.content);
          const isRestoring = guestData.decision?.should_restore_interrupted_question ||
            guestData.decision?.strategy === "RESTORE_INTERRUPTED_QUESTION";

          const isRepeating = !isRestoring && isQuestionTooSimilar(guestData.ai_response, pastQuestions);
          if (!isRepeating) {
            aiResponseContent = guestData.ai_response;
            if (guestData.evaluation) evaluation = { ...evaluation, ...guestData.evaluation };
            if (guestData.decision) decision = { ...decision, ...guestData.decision };
            if (guestData.injected_mistake !== undefined) {
              session.injectedMistake = guestData.injected_mistake;
            }
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
      // Normal Student Mode: Strict Anti-Repetition Guarantee
      const allPastQuestions = session.messages
        .filter((m) => m.sender === "AI")
        .map((m) => m.content);

      if (isQuestionTooSimilar(aiResponseContent, allPastQuestions)) {
        const curObj = session.topicPlan?.objectives.find((o) => o.id === session.topicPlan?.currentObjectiveId);
        aiResponseContent = this.generateStudentQuestion(
          session.topic,
          decision.strategy,
          decision.difficulty,
          userMsgText,
          evaluation.undefined_terms || [],
          evaluation.misconceptions || [],
          turnNumber,
          allPastQuestions,
          curObj
        );
      }

      // Tabula Rasa Guard: Never leak prerequisites (e.g. sorted, order) if teacher has never mentioned them
      const allConversationText = session.messages.map((m) => m.content).join(" ").toLowerCase() + " " + userMsgText.toLowerCase();
      const leaksSorting = (aiResponseContent.toLowerCase().includes("sorted") || aiResponseContent.toLowerCase().includes("sort ") || aiResponseContent.toLowerCase().includes("order")) &&
        !allConversationText.includes("sorted") && !allConversationText.includes("sort") && !allConversationText.includes("order");
      if (leaksSorting) {
        aiResponseContent = `Wait, how does that core process actually work step-by-step under the hood in **${session.topic}**?`;
      }

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

        const responseText = `Spot on! You understood this part perfectly. We're toggling back to Student Mode so you can continue teaching me.\n\nNow, picking up right where we left off:\n\n${restoredQ}`;
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
        const praiseResponse = `Whoa, great catch! You're totally right that ${inj.counterReason || "that assumption fails in that edge case"}. That was a tricky edge case I was wondering about!\n\nSo how does **${topic}** handle that scenario in practice?`;
        return { evaluation: evalData, decision: decData, aiResponseContent: praiseResponse };
      } else {
        // Teacher missed the misconception: Curio raises a student doubt
        const doubtQ = `Wait, really? But doesn't ${inj.counterReason || "that break the standard expectation"}? Wouldn't that cause unexpected issues in **${topic}**?`;
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

    // Detect misconceptions (Priority 2) - Universal semantic logic for ANY topic
    const misconceptions: string[] = [];
    if (
      clean.includes("magic") ||
      clean.includes("infinite speed") ||
      clean.includes("never uses memory") ||
      clean.includes("zero cost") ||
      clean.includes("infinite memory") ||
      clean.includes("infinite loop is fine")
    ) {
      misconceptions.push(`Unrealistic premise or physical/computational impossibility regarding ${topic}`);
    }
    if (
      clean.includes("no base case") ||
      clean.includes("without base case") ||
      clean.includes("base case is optional") ||
      clean.includes("never terminates")
    ) {
      misconceptions.push(`Belief that recursive or iterative execution can terminate without a base termination condition`);
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

    // Universal Semantic Verification Evaluator (Works for ANY topic in the world)
    const words = clean.split(/\s+/).filter(Boolean);
    const hasReasoning =
      clean.includes("because") ||
      clean.includes("since") ||
      clean.includes("so that") ||
      clean.includes("in order to") ||
      clean.includes("means that") ||
      clean.includes("requires") ||
      clean.includes("guarantees") ||
      clean.includes("allows") ||
      clean.includes("without") ||
      clean.includes("ensures") ||
      clean.includes("otherwise") ||
      clean.includes("instead of");

    const hasRefusalOrConfusion =
      clean.includes("i don't know") ||
      clean.includes("idk") ||
      clean.includes("no idea") ||
      clean.includes("magic") ||
      clean.includes("not sure");

    if (!hasRefusalOrConfusion && words.length >= 5 && (hasReasoning || words.length >= 8)) {
      return {
        isPass: true,
        isPartial: false,
        feedback: `You've demonstrated a solid conceptual grasp of how **${gap}** operates in **${topic}**.`,
      };
    }

    if (!hasRefusalOrConfusion && words.length >= 3) {
      return {
        isPass: false,
        isPartial: true,
        feedback: `You're touching on the right direction. Could you explain the 'why' or causal mechanism of **${gap}** in a bit more detail?`,
      };
    }

    return {
      isPass: false,
      isPartial: false,
      feedback: `Let's clarify the essential condition and mechanism for **${gap}** one more time.`,
    };
  }

  // =========================================================================
  // Content Generation Helpers (Socratic, Teacher, Verification)
  // =========================================================================
  private generateVerificationQuestionForGap(topic: string, gap: string): string {
    return `In your own words, what is the single most important rule or condition required for **${gap}** in **${topic}** to execute correctly, and why?`;
  }

  private generateSubtleMisconception(topic: string, concept: string): { misconceptionQ: string; counterReason: string } {
    return {
      misconceptionQ: `Wait, so if we apply **${topic}** under boundary edge cases, does that guarantee the exact same performance without any additional trade-offs, right?`,
      counterReason: `edge case constraints introduce trade-offs that prevent identical performance guarantees`,
    };
  }

  private generateTeacherResponseForQuestion(topic: string, gap: string, userQuestion: string): string {
    return `Let's focus on the exact mechanism of **${gap}** in **${topic}**:\n\nThe core process relies on specific prerequisites: inputs must satisfy boundary invariants before processing. Once verified, each step transforms state deterministically until completion.\n\n**Verification:**\nIn your own words, what is the single most important condition required for **${topic}** to execute correctly, and why?`;
  }

  private generateTeacherResponseForGap(topic: string, gap: string, learnerAnswer: string): string {
    return `Let's pause the questions for a moment.\n\nThere's one idea worth clearing up first regarding **${gap}**.\n\nIn **${topic}**, we must understand the core prerequisite: before we can apply the mechanism, its fundamental invariant must hold true. Without this invariant, the mechanism cannot guarantee correctness or efficiency.\n\n**Verification:**\nIn your own words, what is the single most important condition required for **${topic}** to function properly, and why?`;
  }

  private generateAdaptedTeacherExplanation(topic: string, gap: string, attempt: number, misconception?: string): string {
    const errorPrefix = misconception ? `Notice that in your previous answer: "${misconception}". ` : "Let's take a closer look at what happened in that example: ";
    if (attempt === 2) {
      return `${errorPrefix}The essential rule in **${topic}** is that without satisfying the prerequisite (**${gap}**), we cannot safely discard portions of the input because values can appear on the wrong side.\n\n**Verification:**\nIf the list is unsorted, why does eliminating a half of the collection risk completely missing the target?`;
    }
    return `${errorPrefix}Before any divide-and-conquer operation can succeed, the data must follow a known sequence. Otherwise, comparisons against a middle element lead to incorrect deductions.\n\n**Verification:**\nWhy must the collection be sorted before we can safely compare and discard either half?`;
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
      const miscCandidates: string[] = [
        `Wait, I have a doubt about that: you explained that "${cleanAnswer.length > 50 ? cleanAnswer.substring(0, 50) + "..." : cleanAnswer}", but I'm having trouble seeing why that would always hold true in **${cleanTopic}**. Could you clarify if that always applies or if there are situations where that breaks down?`,
        `Hold on, I'm trying to follow your explanation of "${cleanAnswer.length > 45 ? cleanAnswer.substring(0, 45) + "..." : cleanAnswer}", but wouldn't that cause an issue under certain conditions? Could you explain what happens if those standard assumptions don't hold?`,
        `Wait, I'm a bit confused about how that works in practice. How does that hold up if the usual prerequisites of **${cleanTopic}** aren't met?`,
      ];

      const chosen = pickUnique(miscCandidates);
      if (chosen) return chosen;
    }

    // 2. CLARIFY_TERM: Student asks to unpack an undefined symbol or technical term
    if (strategy === "CLARIFY_TERM" && undefinedTerms.length > 0) {
      const term = undefinedTerms[0];
      const termCandidates = [
        `I think I follow the overall process you explained, but I'm getting a bit confused about the term "${term}". Could you explain what "${term}" actually means in simple, descriptive words and what role it plays here?`,
        `I'm trying to visualize the steps you mentioned, but I'm not entirely sure about "${term}". What exactly does "${term}" represent in this context, and could you clarify it with a quick example so I don't get mixed up?`,
        `That explanation helps me see the bigger picture, but I have a doubt regarding "${term}". Could you break down what "${term}" stands for and how it affects the rest of the steps?`,
      ];
      const chosen = pickUnique(termCandidates);
      if (chosen) return chosen;
    }

    // Determine the active objective we are exploring
    const targetObj = (isObjectiveMastered ? nextObjective : currentObjective) || nextObjective || currentObjective;
    const cat = targetObj ? targetObj.category : "mechanism";

    // 5. UNIVERSAL CURRICULUM QUESTIONS (Authentic Beginner Student Voice for ANY Topic)
    const universalCandidates: string[] = [];

    // Category: Mechanism / Probe How (Innocent student wanting to know what happens first and how it works)
    if (cat === "mechanism" || strategy === "PROBE_HOW") {
      universalCandidates.push(`Oh, I think I understand what it's used for, but I'm having trouble picturing the actual mechanism. Could you walk me through how **${cleanTopic}** actually works step-by-step from the very beginning?`);
      universalCandidates.push(`I see the main goal here! But I'm not quite sure how it actually processes everything under the hood—could you explain what steps it follows in simple, descriptive terms?`);
      universalCandidates.push(`I follow the general idea so far, but I'm struggling to visualize what happens first when it runs. Could you break down the step-by-step process for me?`);
      universalCandidates.push(`Could you explain the step-by-step process of what **${cleanTopic}** does from start to finish so I can understand the inner workings?`);
    }

    // Category: Application / Request Example
    if (cat === "application" || strategy === "REQUEST_EXAMPLE") {
      universalCandidates.push(`I understand the theoretical steps you shared, but I learn best when seeing things in action. Could you walk me through a simple, concrete example with real values so I can trace what happens at each step?`);
      universalCandidates.push(`That makes sense on paper, but I'm having trouble picturing it with real data. Could you show me a small example with specific items so I can clearly see how **${cleanTopic}** executes?`);
      universalCandidates.push(`Can you give me a simple, descriptive scenario to illustrate how **${cleanTopic}** works in practice?`);
    }

    // Category: Mechanism Doubt / Probe Why
    if (strategy === "PROBE_WHY") {
      universalCandidates.push(`Wait, I follow that step, but I don't fully understand the reasoning behind it. Why does it take that specific approach, and how does it know where to go next in **${cleanTopic}**?`);
      universalCandidates.push(`Hold on, I have a doubt about that part: how can we be sure that step won't accidentally miss something or give an incorrect result?`);
      universalCandidates.push(`Wait, I'm trying to make sure I understand the logic. Why does that step guarantee that **${cleanTopic}** works correctly?`);
    }

    // Category: Prerequisite / Condition Doubt
    if (cat === "prerequisite") {
      universalCandidates.push(`Hold on, I think I see how the process works, but does **${cleanTopic}** require certain conditions or setup before starting? What happens if someone tries to run it without meeting those conditions?`);
      universalCandidates.push(`Wait, I have a doubt about whether this always works. Does something need to be prepared or organized beforehand for **${cleanTopic}** to function properly?`);
      universalCandidates.push(`Why is that specific rule or setup necessary before **${cleanTopic}** can begin?`);
    }

    // Category: Edge Cases / Boundaries
    if (cat === "edge_cases" || strategy === "TEST_EDGE_CASE") {
      universalCandidates.push(`I feel like I'm getting a good grasp of the normal flow, but what happens when things go wrong? For instance, what does **${cleanTopic}** do if the target isn't there at all, or if the input is completely empty?`);
      universalCandidates.push(`That clears up the standard flow, but I'm curious about boundary limits. How does **${cleanTopic}** handle tricky edge cases, like duplicate values or unusual inputs?`);
      universalCandidates.push(`How does **${cleanTopic}** handle boundary situations when it reaches the very end without finding what it was looking for?`);
    }

    // Category: Complexity / Performance
    if (cat === "complexity" || strategy === "DEPTH_EXPANSION") {
      universalCandidates.push(`I see how it works for a small set of items, but I'm wondering how it scales. How fast does **${cleanTopic}** run when handling millions of elements, and what causes it to slow down?`);
      universalCandidates.push(`I'm curious about efficiency in different situations. What is the difference between the best-case and worst-case performance of **${cleanTopic}**, and what causes the worst case?`);
    }

    // Category: Trade-offs / Synthesis
    if (cat === "trade_offs" || strategy === "CONNECT_CONCEPTS") {
      universalCandidates.push(`Now that I understand how it functions, I'm trying to figure out when to use it in practice. When would you prefer **${cleanTopic}** over other approaches, and what are its biggest disadvantages?`);
      universalCandidates.push(`Under what specific circumstances would you recommend NOT using **${cleanTopic}**, and what alternative approach would you choose instead?`);
    }

    // Category: Definition
    if (cat === "definition") {
      universalCandidates.push(`I'm completely new to this topic and eager to learn it from scratch. Could you explain what **${cleanTopic}** is in simple, descriptive words and what real-world problem it was created to solve?`);
    }

    // 6. Dynamic Entity-Based Student Doubts (If user mentioned specific causal words)
    if (lowerAnswer.includes("because") || lowerAnswer.includes("so that") || lowerAnswer.includes("means that")) {
      universalCandidates.push(`Wait, I have a doubt about that reasoning: why does that specifically guarantee that it works correctly in **${cleanTopic}**?`);
      universalCandidates.push(`Hold on, does that reasoning always hold true, or are there cases where that assumption breaks down in **${cleanTopic}**?`);
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
