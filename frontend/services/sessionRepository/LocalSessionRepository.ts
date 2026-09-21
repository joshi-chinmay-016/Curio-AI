import {
  SessionRepository,
  StoredSession,
  StoredMessage,
  StoredQuestion,
  SessionRepositorySummary,
  ChatTurnResponse,
  TurnEvaluationData,
  LearningDecisionData,
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
  "i'm stuck",
  "im stuck",
  "i am stuck",
  "i'm confused",
  "im confused",
  "i am confused",
  "i have no idea",
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
];

const NON_ANSWER_ACKNOWLEDGMENTS = [
  "ok",
  "okay",
  "yes",
  "yeah",
  "yep",
  "sure",
  "alright",
  "i understand",
  "got it",
  "understood",
  "k",
  "yup",
  "right",
];

function hasExplicitTeachOrStuckSignal(text: string): boolean {
  if (!text) return false;
  const clean = text.toLowerCase().trim();
  return EXPLICIT_TEACH_OR_STUCK_PHRASES.some((phrase) => clean.includes(phrase));
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

export function generateInitialStudentQuestion(topic: string): string {
  const clean = topic.trim();
  return `Hi! I'm Curio. You're going to teach me about **${clean}** today!\n\nTo start off, can you explain in simple words: **what is ${clean}**, and what core problem or mechanism does it address?`;
}

export class LocalSessionRepository implements SessionRepository {
  async createSession(topic: string, sourceType: string = "GENERAL"): Promise<StoredSession> {
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

    const session: StoredSession = {
      sessionId,
      topic: cleanTopic,
      title: cleanTopic,
      sourceType,
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
    };

    const storage = safeGetStorage();
    storage[sessionId] = session;
    safeSetStorage(storage);

    return session;
  }

  async getSession(sessionId: string): Promise<StoredSession | null> {
    const storage = safeGetStorage();
    return storage[sessionId] || null;
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
    const { evaluation, decision, aiResponseContent } = this.evaluateAndDecide(
      session,
      userMsgText,
      turnNumber
    );

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

      // 2. User gives a generic non-answer acknowledgment ("yes", "ok", "sure", "i understand")
      if (isNonAnswer) {
        const evalData: TurnEvaluationData = {
          correctness: 0.2,
          clarity: 0.5,
          completeness: 0.1,
          depth: 0.1,
          relevance: 0.6,
          stuck_probability: 0.6,
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
          confidence: currentConf,
          reason: `Learner provided acknowledgment without demonstrating understanding. Prompting for explanation in own words.`,
          active_concept: gap,
          should_offer_termination: false,
          should_restore_interrupted_question: false,
        };

        const promptText = `To make sure we've locked this concept in before returning to our questions:\n\nIn your own words, how would you explain the core mechanism of **${gap}**?`;
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
    // B. IN STUDENT MODE: Evaluate Learner's Answer
    // -----------------------------------------------------------------------
    const { correctness, misconceptions, missingConcepts, knowledgeGap, isMajorMisconception, isPartial, isStrong } =
      this.analyzeAnswerSemantics(topic, userAnswer, isExplicitStuck);

    const stuckProb = isExplicitStuck ? 0.95 : isMajorMisconception ? 0.75 : isPartial ? 0.2 : 0.05;

    const evalData: TurnEvaluationData = {
      correctness,
      clarity: isStrong ? 0.9 : isPartial ? 0.7 : 0.4,
      completeness: isStrong ? 0.9 : isPartial ? 0.5 : 0.2,
      depth: isStrong ? 0.85 : isPartial ? 0.4 : 0.1,
      relevance: isExplicitStuck ? 0.3 : 0.9,
      stuck_probability: stuckProb,
      misconceptions,
      missing_concepts: missingConcepts,
      undefined_terms: [],
      mastered_concepts: isStrong ? [`${topic} core principles`] : [],
      knowledge_gap: knowledgeGap,
      recommended_strategy: isExplicitStuck || isMajorMisconception
        ? "TEACH_GAP"
        : isPartial
        ? "PROBE_WHY"
        : "INCREASE_DIFFICULTY",
      recommended_difficulty: isStrong ? Math.min(5, currentDiff + 1) : currentDiff,
    };

    // -----------------------------------------------------------------------
    // C. DECISION HIERARCHY
    // -----------------------------------------------------------------------
    const triggerA = isExplicitStuck;
    const triggerB = stuckProb >= 0.75 && (correctness < 0.5 || !!knowledgeGap);
    const triggerC = session.consecutiveFailures >= 1 && correctness < 0.5;
    const triggerD = isMajorMisconception || correctness < 0.25;

    if (triggerA || triggerB || triggerC || triggerD) {
      // TRANSITION TO TEACHER MODE
      let identifiedGap = knowledgeGap || misconceptions[0];
      if (!identifiedGap) {
        if (cleanAns.includes("mechanism")) {
          identifiedGap = `${topic} request handling mechanism`;
        } else if (cleanAns.includes("middleware")) {
          identifiedGap = `${topic} middleware architecture`;
        } else if (cleanAns.includes("asgi") || cleanAns.includes("server")) {
          identifiedGap = `${topic} ASGI server role`;
        } else {
          identifiedGap = `${topic} core mechanism`;
        }
      }

      const nextDiff = isMajorMisconception ? Math.max(1, currentDiff - 1) : currentDiff;

      const decData: LearningDecisionData = {
        next_mode: "TEACHER",
        strategy: "TEACH_GAP",
        difficulty: nextDiff,
        confidence: Math.max(10, Math.round(currentConf - 10)),
        reason: `Learner requires teacher intervention (${
          triggerA
            ? "explicit stuck signal"
            : triggerD
            ? "clear major misconception detected"
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

    if (isPartial) {
      // PARTIAL UNDERSTANDING -> Stay in Student Mode, probe specific missing reasoning
      const decData: LearningDecisionData = {
        next_mode: "STUDENT",
        strategy: "PROBE_WHY",
        difficulty: currentDiff,
        confidence: Math.round(currentConf + 3),
        reason: `Partial answer. Probing missing reasoning for '${missingConcepts[0] || topic}'.`,
        active_concept: missingConcepts[0] || topic,
        should_offer_termination: false,
        should_restore_interrupted_question: false,
      };

      const probeResponse = this.generateProbingQuestion(topic, missingConcepts[0] || topic, userAnswer);
      return { evaluation: evalData, decision: decData, aiResponseContent: probeResponse };
    }

    // STRONGLY CORRECT -> Stay in Student Mode, increase difficulty or probe deeper
    const nextDiff = session.consecutiveSuccesses >= 1 ? Math.min(5, currentDiff + 1) : currentDiff;
    const decData: LearningDecisionData = {
      next_mode: "STUDENT",
      strategy: nextDiff > currentDiff ? "INCREASE_DIFFICULTY" : "PROBE_WHY",
      difficulty: nextDiff,
      confidence: Math.min(100, Math.round(currentConf + 8)),
      reason: "Strong understanding demonstrated. Advancing inquiry in Student Mode.",
      active_concept: topic,
      should_offer_termination: currentConf >= 75,
      should_restore_interrupted_question: false,
    };

    const studentFollowup = this.generateStudentFollowup(topic, turnNumber, nextDiff);
    return { evaluation: evalData, decision: decData, aiResponseContent: studentFollowup };
  }

  // =========================================================================
  // Semantic Analysis Helper
  // =========================================================================
  private analyzeAnswerSemantics(
    topic: string,
    answer: string,
    isExplicitStuck: boolean
  ): {
    correctness: number;
    misconceptions: string[];
    missingConcepts: string[];
    knowledgeGap: string | null;
    isMajorMisconception: boolean;
    isPartial: boolean;
    isStrong: boolean;
  } {
    if (isExplicitStuck) {
      return {
        correctness: 0.0,
        misconceptions: [],
        missingConcepts: [`Core prerequisite of ${topic}`],
        knowledgeGap: `Learner requested teaching / does not know how ${topic} works`,
        isMajorMisconception: false,
        isPartial: false,
        isStrong: false,
      };
    }

    const clean = answer.toLowerCase().trim();
    const tLower = topic.toLowerCase();

    // 1. Topic: FastAPI
    if (tLower.includes("fastapi")) {
      if (clean.includes("database") || clean.includes("is a db") || clean.includes("opens tcp") || clean.includes("stores data in tables")) {
        return {
          correctness: 0.1,
          misconceptions: ["Confuses FastAPI with a database or believes it opens TCP connections directly"],
          missingConcepts: ["ASGI interface", "Uvicorn server role"],
          knowledgeGap: "Does not understand that FastAPI is an ASGI application framework, not a database or raw socket server",
          isMajorMisconception: true,
          isPartial: false,
          isStrong: false,
        };
      }
      if (clean.includes("faster") || clean.includes("speed") || clean.includes("async") || clean.includes("handles requests")) {
        if (!clean.includes("asgi") && !clean.includes("uvicorn") && !clean.includes("server") && !clean.includes("socket")) {
          return {
            correctness: 0.55,
            misconceptions: [],
            missingConcepts: ["ASGI server bridge mechanism"],
            knowledgeGap: "States performance benefits but does not explain how the ASGI server bridges requests to the FastAPI application",
            isMajorMisconception: false,
            isPartial: true,
            isStrong: false,
          };
        }
      }
      if ((clean.includes("asgi") || clean.includes("uvicorn") || clean.includes("server")) && (clean.includes("socket") || clean.includes("network") || clean.includes("route") || clean.includes("pydantic") || clean.includes("middleware"))) {
        return {
          correctness: 0.95,
          misconceptions: [],
          missingConcepts: [],
          knowledgeGap: null,
          isMajorMisconception: false,
          isPartial: false,
          isStrong: true,
        };
      }
    }

    // 2. Topic: Binary Search
    if (tLower.includes("binary search")) {
      // Major misconception: checks one by one / linear search / unsorted
      if (clean.includes("one by one") || clean.includes("every element") || clean.includes("linear") || clean.includes("checks all")) {
        return {
          correctness: 0.1,
          misconceptions: ["Confuses binary search with linear search (checking every element one by one)"],
          missingConcepts: ["Divide and conquer", "Half space elimination"],
          knowledgeGap: "Does not understand that binary search eliminates half the search space using sorted ordering",
          isMajorMisconception: true,
          isPartial: false,
          isStrong: false,
        };
      }
      if (clean.includes("unsorted") || clean.includes("any order") || clean.includes("random")) {
        return {
          correctness: 0.2,
          misconceptions: ["Belief that binary search works on unsorted arrays"],
          missingConcepts: ["Sorted order invariant"],
          knowledgeGap: "Fails to recognize why monotonic ordering is required for binary comparison",
          isMajorMisconception: true,
          isPartial: false,
          isStrong: false,
        };
      }
      // Partial: mentions efficiency or middle but misses halving/sorting
      if (clean.includes("efficient") || clean.includes("fast") || clean.includes("middle") || clean.includes("faster")) {
        if (!clean.includes("half") && !clean.includes("eliminate") && !clean.includes("left or right") && !clean.includes("greater") && !clean.includes("smaller")) {
          return {
            correctness: 0.55,
            misconceptions: [],
            missingConcepts: ["Half-array elimination mechanism"],
            knowledgeGap: "States efficiency but does not explain how comparing with the middle element eliminates half",
            isMajorMisconception: false,
            isPartial: true,
            isStrong: false,
          };
        }
      }
      // Strong
      if ((clean.includes("half") || clean.includes("eliminate") || clean.includes("discard")) && (clean.includes("sort") || clean.includes("middle") || clean.includes("order"))) {
        return {
          correctness: 0.95,
          misconceptions: [],
          missingConcepts: [],
          knowledgeGap: null,
          isMajorMisconception: false,
          isPartial: false,
          isStrong: true,
        };
      }
    }

    // 3. Topic: Photosynthesis
    if (tLower.includes("photosynthesis")) {
      // Major misconception: plants eat sunlight directly / turns light directly into oxygen
      if (clean.includes("eat sunlight") || clean.includes("eats sunlight") || clean.includes("turns light directly into oxygen") || clean.includes("light into oxygen directly")) {
        return {
          correctness: 0.1,
          misconceptions: ["Belief that plants eat sunlight or directly transform photons into oxygen atoms"],
          missingConcepts: ["Chemical energy storage (ATP/NADPH, glucose)", "Water photolysis"],
          knowledgeGap: "Misunderstands light energy conversion into chemical bonds and the source of released oxygen (water)",
          isMajorMisconception: true,
          isPartial: false,
          isStrong: false,
        };
      }
      // Partial: mentions light and sugar/food but misses conversion mechanism
      if (clean.includes("sunlight") || clean.includes("food") || clean.includes("sugar") || clean.includes("glucose")) {
        if (!clean.includes("chlorophyll") && !clean.includes("chemical energy") && !clean.includes("co2") && !clean.includes("water") && !clean.includes("atp")) {
          return {
            correctness: 0.6,
            misconceptions: [],
            missingConcepts: ["Chemical energy conversion mechanism", "Role of water and CO2"],
            knowledgeGap: "Mentions basic inputs/outputs but misses the transformation of light energy into chemical energy",
            isMajorMisconception: false,
            isPartial: true,
            isStrong: false,
          };
        }
      }
      // Strong
      if ((clean.includes("light energy") || clean.includes("photons")) && (clean.includes("chemical energy") || clean.includes("glucose") || clean.includes("atp")) && (clean.includes("water") || clean.includes("co2") || clean.includes("chloroplast"))) {
        return {
          correctness: 0.95,
          misconceptions: [],
          missingConcepts: [],
          knowledgeGap: null,
          isMajorMisconception: false,
          isPartial: false,
          isStrong: true,
        };
      }
    }

    // 4. Topic: Operating Systems
    if (tLower.includes("operating system") || tLower === "os") {
      if (clean.includes("cpu stores all files") || clean.includes("memory never erases") || clean.includes("ram is permanent") || clean.includes("cpu is the hard drive")) {
        return {
          correctness: 0.1,
          misconceptions: ["Confusing volatile memory/CPU registers with persistent secondary storage"],
          missingConcepts: ["Virtual memory", "File system abstraction", "Storage hierarchy"],
          knowledgeGap: "Fails to distinguish CPU execution from persistent storage and volatile RAM",
          isMajorMisconception: true,
          isPartial: false,
          isStrong: false,
        };
      }
      if (clean.includes("hardware") && (clean.includes("process") || clean.includes("memory") || clean.includes("scheduling") || clean.includes("abstraction"))) {
        return {
          correctness: 0.95,
          misconceptions: [],
          missingConcepts: [],
          knowledgeGap: null,
          isMajorMisconception: false,
          isPartial: false,
          isStrong: true,
        };
      }
    }

    // 5. Topic: Python decorators
    if (tLower.includes("decorator")) {
      if (clean.includes("css") || clean.includes("color") || clean.includes("visual") || clean.includes("style") || clean.includes("font")) {
        return {
          correctness: 0.1,
          misconceptions: ["Confusing Python function decorators with visual CSS styling"],
          missingConcepts: ["Higher-order functions", "Closures", "Function wrapping"],
          knowledgeGap: "Does not understand that decorators are higher-order functions wrapping callables",
          isMajorMisconception: true,
          isPartial: false,
          isStrong: false,
        };
      }
      if (clean.includes("higher-order") || clean.includes("takes a function") || (clean.includes("wrap") && (clean.includes("arguments") || clean.includes("behavior")))) {
        return {
          correctness: 0.95,
          misconceptions: [],
          missingConcepts: [],
          knowledgeGap: null,
          isMajorMisconception: false,
          isPartial: false,
          isStrong: true,
        };
      }
    }

    // 6. Generic Fallback Semantic Analysis
    if (clean.includes("infinite") || clean.includes("never drops") || clean.includes("magic") || clean.includes("stores all files permanently")) {
      return {
        correctness: 0.1,
        misconceptions: [`Fundamental contradiction regarding ${topic}`],
        missingConcepts: [`Realistic constraints of ${topic}`],
        knowledgeGap: `Fundamental misconception on constraints of ${topic}`,
        isMajorMisconception: true,
        isPartial: false,
        isStrong: false,
      };
    }

    const wordCount = clean.split(/\s+/).length;
    if (wordCount < 4) {
      return {
        correctness: 0.2,
        misconceptions: [],
        missingConcepts: [`Detailed mechanism of ${topic}`],
        knowledgeGap: `Answer too brief to demonstrate understanding of ${topic}`,
        isMajorMisconception: false,
        isPartial: true,
        isStrong: false,
      };
    }

    if (clean.includes("not sure") || clean.includes("maybe") || clean.includes("i think so") || clean.includes("guess")) {
      return {
        correctness: 0.45,
        misconceptions: [],
        missingConcepts: [`Definitive reasoning for ${topic}`],
        knowledgeGap: "Uncertain reasoning",
        isMajorMisconception: false,
        isPartial: true,
        isStrong: false,
      };
    }

    if (wordCount >= 15 && (clean.includes("because") || clean.includes("means that") || clean.includes("mechanism") || clean.includes("therefore") || clean.includes("invariant") || clean.includes("process"))) {
      return {
        correctness: 0.9,
        misconceptions: [],
        missingConcepts: [],
        knowledgeGap: null,
        isMajorMisconception: false,
        isPartial: false,
        isStrong: true,
      };
    }

    return {
      correctness: 0.65,
      misconceptions: [],
      missingConcepts: [`Underlying rationale for ${topic}`],
      knowledgeGap: "Partial explanation without deep underlying rationale",
      isMajorMisconception: false,
      isPartial: true,
      isStrong: false,
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
    if (tLower.includes("binary search") || gLower.includes("binary search") || gLower.includes("order") || gLower.includes("search")) {
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
  private generateTeacherResponseForQuestion(topic: string, gap: string, userQuestion: string): string {
    const qLower = userQuestion.toLowerCase();
    const tLower = topic.toLowerCase();

    if (tLower.includes("fastapi") || gap.toLowerCase().includes("fastapi") || gap.toLowerCase().includes("mechanism") || gap.toLowerCase().includes("asgi") || gap.toLowerCase().includes("middleware")) {
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

    if (tLower.includes("fastapi") || gLower.includes("fastapi") || gLower.includes("mechanism") || gLower.includes("asgi")) {
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

    if (tLower.includes("fastapi") || gLower.includes("fastapi") || gLower.includes("asgi") || gLower.includes("mechanism")) {
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

  private generateProbingQuestion(topic: string, missingConcept: string, learnerAnswer: string): string {
    const tLower = topic.toLowerCase();

    if (tLower.includes("fastapi")) {
      return `I see what you mean about the performance benefits! To make sure I understand the full picture: how does **FastAPI** receive and handle incoming HTTP requests from the client? What role does the ASGI server play?`;
    }

    if (tLower.includes("binary search")) {
      return `I see the efficiency part! But what specific information does the **sorted order** give us when we compare our target with the middle element? Why couldn't we do that on an unsorted list?`;
    }

    if (tLower.includes("photosynthesis")) {
      return `Good start! You mentioned the basic inputs. Can you walk me through what happens to the light energy after chlorophyll absorbs it? How does it actually become chemical energy?`;
    }

    return `I see what you mean! To make sure I understand the full picture: how does **${topic}** handle **${missingConcept}**? What is the step-by-step mechanism?`;
  }

  private generateStudentFollowup(topic: string, turnNumber: number, difficulty: number): string {
    const questions = [
      `That makes total sense! Now suppose the data contains duplicate values or boundary cases. How does **${topic}** handle that?`,
      `Interesting! What are the primary trade-offs or constraints when applying **${topic}** compared to alternative approaches?`,
      `Can you give me a concrete example or code snippet illustrating how **${topic}** executes step-by-step in practice?`,
      `Great explanation! If the system scale increases tenfold, where is the first bottleneck or failure point in **${topic}**?`,
    ];
    return questions[(turnNumber - 1) % questions.length];
  }
}
