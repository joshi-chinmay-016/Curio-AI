import {
  GapReport,
  ConceptCell,
  Gap,
  TopicOption,
  UnderstandingLayer,
  ConceptStatus,
  GapSeverity,
  MasteryLevel,
  EvidenceItem,
} from "@/types/gapReport";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface SessionSummary {
  session_id: string;
  topic: string;
  status: string;
  current_mode?: string;
  difficulty?: number;
  confidence?: number;
  created_at: string;
  last_active_at: string;
}

export interface BackendReportResponse {
  session_id: string;
  understanding_score: number;
  mastery_level: string;
  strengths: string[];
  high_priority_learning_gaps: string[];
  medium_priority_learning_gaps: string[];
  low_priority_learning_gaps: string[];
  misconceptions_detected: string[];
  concepts_mastered: string[];
  teacher_interventions_required: number;
  difficulty_achieved: number;
  personalized_roadmap: any[];
  recommended_exercises: any[];
  evidence_confidence: number;
  concept_assessments: any[];
  resolved_gaps: string[];
  unresolved_gaps: string[];
  resolved_misconceptions: string[];
  unresolved_misconceptions: string[];
  session_evaluation?: any;
  created_at: string;
}

/**
 * Fetch all available sessions from the backend.
 */
export async function getSessions(): Promise<SessionSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      console.warn(`Failed to fetch sessions: status ${res.status}`);
      return [];
    }

    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.warn("Backend sessions endpoint unavailable:", err);
    return [];
  }
}

/**
 * Trigger explicit evaluation and compile report for a session.
 */
export async function evaluateSession(sessionId: string): Promise<GapReport | null> {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error(`Evaluation failed (${res.status}):`, errorText);
      return null;
    }

    const reportData: BackendReportResponse = await res.json();
    const sessions = await getSessions();
    const currentSession = sessions.find((s) => s.session_id === sessionId);
    const topicName = currentSession?.topic || "Learning Session";
    const availableTopics: TopicOption[] = sessions.map((s) => ({
      id: s.session_id,
      name: s.topic,
    }));

    return mapBackendReportToGapReport(reportData, topicName, availableTopics);
  } catch (err) {
    console.error("Failed to trigger session evaluation:", err);
    return null;
  }
}

/**
 * Fetch Gap Report strictly from backend.
 * Returns null if no report exists for the session or if no sessions exist.
 */
export async function getGapReport(
  sessionId?: string
): Promise<GapReport | null> {
  const sessions = await getSessions();

  if (!sessionId) {
    // If no sessionId specified, pick the most recent session with a completed report
    if (sessions.length === 0) {
      return null;
    }
    sessionId = sessions[0].session_id;
  }

  const currentSession = sessions.find((s) => s.session_id === sessionId);
  const topicName = currentSession?.topic || "Learning Session";
  const availableTopics: TopicOption[] = sessions.map((s) => ({
    id: s.session_id,
    name: s.topic,
  }));

  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/report`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (res.status === 404) {
      // No report has been generated yet for this session
      return null;
    }

    if (!res.ok) {
      console.warn(`Failed to fetch report for session ${sessionId}: status ${res.status}`);
      return null;
    }

    const reportData: BackendReportResponse = await res.json();
    return mapBackendReportToGapReport(reportData, topicName, availableTopics);
  } catch (err) {
    console.warn(`Error fetching report for session ${sessionId}:`, err);
    return null;
  }
}

/**
 * Maps raw backend SessionReportResponse into the frontend GapReport format.
 */
export function mapBackendReportToGapReport(
  backend: BackendReportResponse,
  topicName: string,
  availableTopics: TopicOption[]
): GapReport {
  // 1. Normalize Mastery Level
  const rawMastery = (backend.mastery_level || "DEVELOPING").toUpperCase();
  let masteryLevel: MasteryLevel = "Developing";
  if (rawMastery.includes("BEGIN")) masteryLevel = "Beginner";
  else if (rawMastery.includes("DEV")) masteryLevel = "Developing";
  else if (rawMastery.includes("PROF")) masteryLevel = "Proficient";
  else if (rawMastery.includes("MAST")) masteryLevel = "Mastery";

  // 2. Normalize Confidence (0-100)
  const evidenceConfidence =
    backend.evidence_confidence <= 1
      ? Math.round((backend.evidence_confidence || 0) * 100)
      : Math.round(backend.evidence_confidence || 0);

  // 3. Map Concepts
  const concepts: ConceptCell[] = [];
  const rawAssessments = Array.isArray(backend.concept_assessments)
    ? backend.concept_assessments
    : [];

  if (rawAssessments.length > 0) {
    rawAssessments.forEach((ca: any, index: number) => {
      const name = ca.concept || `Concept ${index + 1}`;
      const id =
        ca.id ||
        name.toLowerCase().replace(/[^a-z0-9]+/g, "-") ||
        `concept-${index}`;

      // Determine layer from assessment or heuristics
      let layer: UnderstandingLayer = "DEFINITION";
      if (
        ca.layer &&
        ["DEFINITION", "MECHANISM", "APPLICATION", "EDGE_CASES"].includes(
          ca.layer
        )
      ) {
        layer = ca.layer as UnderstandingLayer;
      } else {
        const lower = name.toLowerCase();
        if (/def|concept|core|overview|term|type|structure|syntax/.test(lower)) {
          layer = "DEFINITION";
        } else if (
          /mech|process|how|algorithm|halving|midpoint|step|flow|logic/.test(
            lower
          )
        ) {
          layer = "MECHANISM";
        } else if (
          /app|implement|recur|iterat|use|practice|pattern|call/.test(lower)
        ) {
          layer = "APPLICATION";
        } else if (
          /edge|bound|terminat|corner|null|empty|overflow|error|limit/.test(
            lower
          )
        ) {
          layer = "EDGE_CASES";
        } else {
          const fallbackLayers: UnderstandingLayer[] = [
            "DEFINITION",
            "MECHANISM",
            "APPLICATION",
            "EDGE_CASES",
          ];
          layer = fallbackLayers[index % fallbackLayers.length];
        }
      }

      // Determine concept status
      const score = Math.round(ca.understanding_score ?? 0);
      const conf =
        ca.confidence <= 1
          ? Math.round((ca.confidence || 0) * 100)
          : Math.round(ca.confidence || 0);

      let status: ConceptStatus = "DEVELOPING";
      if (ca.misconceptions && ca.misconceptions.length > 0) {
        status = "MISCONCEPTION";
      } else if (
        (ca.gaps && ca.gaps.length > 0) ||
        (backend.unresolved_gaps &&
          backend.unresolved_gaps.some((g) =>
            typeof g === "string" ? g.toLowerCase().includes(name.toLowerCase()) : false
          ))
      ) {
        status = "GAP";
      } else if (score >= 80) {
        status = "STRONG";
      } else if (score === 0 && conf === 0) {
        status = "UNTESTED";
      }

      concepts.push({
        id,
        name,
        layer,
        status,
        score,
        confidence: conf,
        relatedConceptIds: Array.isArray(ca.evidence_references)
          ? ca.evidence_references
          : [],
        description:
          (ca.strengths && ca.strengths[0]) ||
          (ca.gaps && ca.gaps[0]) ||
          ca.description ||
          `Assessment for ${name}`,
      });
    });
  } else {
    // Fallback if concept_assessments was not populated: construct from mastered / gaps
    const mastered = backend.concepts_mastered || [];
    const gaps = backend.high_priority_learning_gaps || [];
    const all = [...mastered, ...gaps];

    all.forEach((name, index) => {
      const fallbackLayers: UnderstandingLayer[] = [
        "DEFINITION",
        "MECHANISM",
        "APPLICATION",
        "EDGE_CASES",
      ];
      const isGap = gaps.includes(name);
      concepts.push({
        id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
        name,
        layer: fallbackLayers[index % fallbackLayers.length],
        status: isGap ? "GAP" : "STRONG",
        score: isGap ? 42 : 88,
        confidence: evidenceConfidence,
        relatedConceptIds: [],
        description: isGap
          ? `Identified learning gap in ${name}`
          : `Demonstrated mastery in ${name}`,
      });
    });
  }

  // 4. Map Gaps
  const gaps: Gap[] = [];
  const rawGaps =
    backend.session_evaluation?.knowledge_gaps ||
    backend.unresolved_gaps ||
    backend.high_priority_learning_gaps ||
    [];

  rawGaps.forEach((g: any, index: number) => {
    const isObject = typeof g === "object" && g !== null;
    const title = isObject ? g.gap || g.title || `Gap ${index + 1}` : String(g);
    const severity: GapSeverity = isObject
      ? (String(g.severity || "HIGH").toUpperCase() as GapSeverity)
      : index === 0
      ? "HIGH"
      : "MEDIUM";

    // Match concept ID
    const matchingConcept = concepts.find((c) =>
      title.toLowerCase().includes(c.name.toLowerCase())
    );
    const conceptId = matchingConcept ? matchingConcept.id : `concept-gap-${index}`;

    // Extract turn evidence if available in session_evaluation
    const evidence: EvidenceItem[] = [];
    if (backend.session_evaluation?.turns && Array.isArray(backend.session_evaluation.turns)) {
      backend.session_evaluation.turns.forEach((t: any, tIdx: number) => {
        if (
          (t.knowledge_gap && title.toLowerCase().includes(String(t.knowledge_gap).toLowerCase())) ||
          (t.misconceptions && t.misconceptions.some((m: string) => title.toLowerCase().includes(m.toLowerCase())))
        ) {
          evidence.push({
            turn: t.turn_number || tIdx + 1,
            timestamp: t.timestamp || `Turn ${tIdx + 1}`,
            curioAsked: t.question || t.curio_asked || "",
            learnerAnswered: t.learner_response || t.learnerAnswered || "",
            detectionType: t.misconceptions?.length ? "misconception" : "gap",
            explanation: t.explanation || "Demonstrated incomplete understanding during this exchange.",
          });
        }
      });
    }

    gaps.push({
      id: isObject && g.id ? g.id : `gap_${index + 1}`,
      conceptId,
      title,
      severity: ["LOW", "MEDIUM", "HIGH"].includes(severity) ? severity : "HIGH",
      status: "UNRESOLVED",
      understandingScore: isObject && g.understanding_score ? g.understanding_score : 42,
      confidence: evidenceConfidence,
      whyDetected:
        isObject && g.why_detected
          ? g.why_detected
          : `Identified as an unresolved gap during session evaluation.`,
      evidence,
      recommendedAction:
        isObject && g.recommended_action
          ? g.recommended_action
          : `Review ${title} and complete targeted practice exercises.`,
      teacherInterventionAttempted: Boolean(isObject && g.teacher_assisted),
      verificationSuccess: false,
    });
  });

  // 5. Recommended Next Steps
  const recommendedNextSteps: string[] = [];
  if (Array.isArray(backend.personalized_roadmap)) {
    backend.personalized_roadmap.forEach((item: any) => {
      if (typeof item === "string") recommendedNextSteps.push(item);
      else if (item && item.title) {
        recommendedNextSteps.push(
          `${item.title}${item.description ? `: ${item.description}` : ""}`
        );
      }
    });
  }
  if (recommendedNextSteps.length === 0 && Array.isArray(backend.recommended_exercises)) {
    backend.recommended_exercises.forEach((ex: any) => {
      if (typeof ex === "string") recommendedNextSteps.push(ex);
    });
  }

  return {
    sessionId: backend.session_id,
    topicName,
    topicId: backend.session_id,
    understandingScore: Math.round(backend.understanding_score || 0),
    masteryLevel,
    evidenceConfidence,
    conceptsExplored: concepts.length,
    knowledgeGaps: gaps.length,
    resolvedMisconceptions: (backend.resolved_misconceptions || []).length,
    concepts,
    gaps,
    availableTopics,
    recommendedNextSteps,
    createdAt: backend.created_at || new Date().toISOString(),
  };
}

// Future operational actions
export async function practiceGap(gapId: string): Promise<void> {
  console.log(`[Practice Gap] Initiating practice session for gap: ${gapId}`);
}

export async function saveGapForLater(gapId: string): Promise<void> {
  console.log(`[Save Gap] Gap ${gapId} marked for later review.`);
}

export async function markConceptForReview(conceptId: string): Promise<void> {
  console.log(`[Review Concept] Concept ${conceptId} marked for targeted review.`);
}
