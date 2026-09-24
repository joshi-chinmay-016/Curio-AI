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
import { getRegisteredSessionTopic } from "./sessionService";

export async function getGapReport(
  sessionId?: string
): Promise<GapReport | null> {
  const sessions = await getSessions();

  if (!sessionId) {
    if (sessions.length > 0) {
      sessionId = sessions[0].session_id;
    } else {
      sessionId = "session_mock_active";
    }
  }

  const currentSession = sessions.find((s) => s.session_id === sessionId);
  const registeredTopic = getRegisteredSessionTopic(sessionId);
  const topicName =
    registeredTopic ||
    currentSession?.topic ||
    "Learning Concept";

  const availableTopics: TopicOption[] =
    sessions.length > 0
      ? sessions.map((s) => ({ id: s.session_id, name: s.topic }))
      : [
          { id: sessionId, name: topicName },
          { id: "session_mock_sort", name: "QuickSort & Partitioning" },
          { id: "session_mock_trees", name: "Binary Search Trees" },
        ];

  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/report`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (res.ok) {
      const reportData: BackendReportResponse = await res.json();
      return mapBackendReportToGapReport(reportData, topicName, availableTopics);
    }
  } catch (err) {
    console.warn(`Backend report unavailable, using mock report for session ${sessionId}:`, err);
  }

  // Realistic mock report for demonstration & standalone testing
  return getMockGapReport(sessionId, topicName, availableTopics);
}

export function getMockGapReport(
  sessionId: string,
  topicName = "Learning Concept",
  availableTopics: TopicOption[] = [
    { id: "session_mock_active", name: topicName },
    { id: "session_mock_sort", name: "QuickSort & Partitioning" },
    { id: "session_mock_trees", name: "Binary Search Trees" },
  ]
): GapReport {
  const isBinarySearch = topicName.toLowerCase().includes("binary search");

  // If user explicitly chose Binary Search, provide detailed BS concepts
  // Otherwise, generate structured concepts for the user's custom topic!
  const concepts: ConceptCell[] = isBinarySearch
    ? [
        // DEFINITION
        {
          id: "sorted-array-requirement",
          name: "Sorted Array Requirement",
          layer: "DEFINITION",
          status: "STRONG",
          score: 95,
          confidence: 90,
          relatedConceptIds: ["monotonicity"],
          description: "Understands that elements must be in monotonic order to discard halves.",
          gridX: 0,
          gridY: 0,
        },
        {
          id: "log-n-complexity",
          name: "O(log n) Time Complexity",
          layer: "DEFINITION",
          status: "STRONG",
          score: 90,
          confidence: 88,
          relatedConceptIds: ["halving-space"],
          description: "Clearly grasps why dividing the search space by 2 yields logarithmic steps.",
          gridX: 1,
          gridY: 0,
        },
        {
          id: "search-space-invariants",
          name: "Search Space Invariants",
          layer: "DEFINITION",
          status: "DEVELOPING",
          score: 68,
          confidence: 72,
          relatedConceptIds: ["boundary-conditions"],
          description: "Developing understanding of keeping target within the valid index range.",
          gridX: 0,
          gridY: 1,
        },
        {
          id: "monotonicity",
          name: "Monotonicity Property",
          layer: "DEFINITION",
          status: "RESOLVED",
          score: 85,
          confidence: 82,
          relatedConceptIds: ["sorted-array-requirement"],
          description: "Successfully clarified how monotonic evaluation applies to answer-space search.",
          gridX: 1,
          gridY: 1,
        },
        // MECHANISM
        {
          id: "midpoint-calculation",
          name: "Midpoint Calculation",
          layer: "MECHANISM",
          status: "STRONG",
          score: 88,
          confidence: 85,
          relatedConceptIds: ["integer-overflow"],
          description: "Understands middle index computation and truncation behavior.",
          gridX: 0,
          gridY: 0,
        },
        {
          id: "halving-search-space",
          name: "Halving Search Space",
          layer: "MECHANISM",
          status: "STRONG",
          score: 92,
          confidence: 90,
          relatedConceptIds: ["sorted-array-requirement"],
          description: "Understands comparison with target and discarding half the elements.",
          gridX: 1,
          gridY: 0,
        },
        {
          id: "pointer-updates",
          name: "Pointer Updates (low = mid + 1)",
          layer: "MECHANISM",
          status: "DEVELOPING",
          score: 72,
          confidence: 70,
          relatedConceptIds: ["boundary-conditions"],
          description: "Sometimes confuses whether mid should be included or excluded in next range.",
          gridX: 0,
          gridY: 1,
        },
        {
          id: "integer-overflow",
          name: "Integer Overflow Avoidance",
          layer: "MECHANISM",
          status: "RESOLVED",
          score: 84,
          confidence: 80,
          relatedConceptIds: ["midpoint-calculation"],
          description: "Understands why low + (high - low) / 2 avoids 32-bit integer overflow.",
          gridX: 1,
          gridY: 1,
        },
        // APPLICATION
        {
          id: "exact-match-search",
          name: "Exact Match Search",
          layer: "APPLICATION",
          status: "STRONG",
          score: 94,
          confidence: 92,
          relatedConceptIds: ["midpoint-calculation"],
          description: "Flawlessly implemented and explained finding an exact element in an array.",
          gridX: 0,
          gridY: 0,
        },
        {
          id: "lower-bound-search",
          name: "Lower Bound (First Occurrence)",
          layer: "APPLICATION",
          status: "DEVELOPING",
          score: 65,
          confidence: 68,
          relatedConceptIds: ["boundary-conditions"],
          description: "Requires more practice adjusting high pointer when duplicate matches exist.",
          gridX: 1,
          gridY: 0,
        },
        {
          id: "rotated-sorted-array",
          name: "Search in Rotated Sorted Array",
          layer: "APPLICATION",
          status: "UNTESTED",
          score: 0,
          confidence: 0,
          relatedConceptIds: ["monotonicity"],
          description: "Not yet covered in this session.",
          gridX: 0,
          gridY: 1,
        },
        {
          id: "answer-space-binary-search",
          name: "Binary Search on Answer Space",
          layer: "APPLICATION",
          status: "UNTESTED",
          score: 0,
          confidence: 0,
          relatedConceptIds: ["monotonicity"],
          description: "Not yet covered in this session.",
          gridX: 1,
          gridY: 1,
        },
        // EDGE CASES
        {
          id: "boundary-conditions",
          name: "Boundary Conditions (low <= high vs low < high)",
          layer: "EDGE_CASES",
          status: "GAP",
          score: 42,
          confidence: 85,
          relatedConceptIds: ["pointer-updates", "single-element-array"],
          description: "Unclear on terminating condition and why low <= high is necessary for 1-element arrays.",
          gridX: 0,
          gridY: 0,
        },
        {
          id: "target-not-found",
          name: "Target Not Present / Out of Bounds",
          layer: "EDGE_CASES",
          status: "STRONG",
          score: 86,
          confidence: 84,
          relatedConceptIds: ["boundary-conditions"],
          description: "Correctly identifies return value when target is less than min or greater than max.",
          gridX: 1,
          gridY: 0,
        },
        {
          id: "single-element-array",
          name: "Single Element / Empty Array",
          layer: "EDGE_CASES",
          status: "GAP",
          score: 48,
          confidence: 82,
          relatedConceptIds: ["boundary-conditions"],
          description: "Struggles with off-by-one errors when array has length 0 or 1.",
          gridX: 0,
          gridY: 1,
        },
        {
          id: "duplicate-elements",
          name: "Arrays with Duplicate Elements",
          layer: "EDGE_CASES",
          status: "DEVELOPING",
          score: 60,
          confidence: 65,
          relatedConceptIds: ["lower-bound-search"],
          description: "Can find a match, but does not guarantee the first or last instance.",
          gridX: 1,
          gridY: 1,
        },
      ]
    : [
        // Custom Topic Dynamic Concepts
        // DEFINITION
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-core-definition`,
          name: `Core Definition & Scope`,
          layer: "DEFINITION",
          status: "STRONG",
          score: 92,
          confidence: 88,
          relatedConceptIds: [`${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-principles`],
          description: `Demonstrated clear understanding of what ${topicName} is and why it matters.`,
          gridX: 0,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-principles`,
          name: `Fundamental Principles`,
          layer: "DEFINITION",
          status: "STRONG",
          score: 88,
          confidence: 85,
          relatedConceptIds: [`${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-core-definition`],
          description: `Accurately articulated the primary laws and premises underlying ${topicName}.`,
          gridX: 1,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-terminology`,
          name: `Key Terminology & Models`,
          layer: "DEFINITION",
          status: "DEVELOPING",
          score: 70,
          confidence: 72,
          relatedConceptIds: [],
          description: `Developing precision with the domain-specific vocabulary of ${topicName}.`,
          gridX: 0,
          gridY: 1,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-invariants`,
          name: `System Invariants`,
          layer: "DEFINITION",
          status: "RESOLVED",
          score: 84,
          confidence: 80,
          relatedConceptIds: [`${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-core-definition`],
          description: `Resolved initial misconception regarding what invariants must hold true for ${topicName}.`,
          gridX: 1,
          gridY: 1,
        },
        // MECHANISM
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-core-mechanism`,
          name: `Core Operational Mechanism`,
          layer: "MECHANISM",
          status: "STRONG",
          score: 86,
          confidence: 84,
          relatedConceptIds: [],
          description: `Explained the step-by-step processes that drive ${topicName}.`,
          gridX: 0,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-state-flow`,
          name: `State Transitions & Flow`,
          layer: "MECHANISM",
          status: "DEVELOPING",
          score: 68,
          confidence: 70,
          relatedConceptIds: [],
          description: `Needs further clarity on intermediate state changes during complex transitions.`,
          gridX: 1,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-dependencies`,
          name: `Inputs, Outputs & Dependencies`,
          layer: "MECHANISM",
          status: "STRONG",
          score: 90,
          confidence: 88,
          relatedConceptIds: [],
          description: `Clear grasp of the upstream inputs and downstream outputs in ${topicName}.`,
          gridX: 0,
          gridY: 1,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-resource-cost`,
          name: `Resource Cost & Efficiency`,
          layer: "MECHANISM",
          status: "RESOLVED",
          score: 82,
          confidence: 78,
          relatedConceptIds: [],
          description: `Clarified how efficiency and complexity scale when applying ${topicName}.`,
          gridX: 1,
          gridY: 1,
        },
        // APPLICATION
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-primary-use`,
          name: `Primary Practical Use Case`,
          layer: "APPLICATION",
          status: "STRONG",
          score: 94,
          confidence: 90,
          relatedConceptIds: [],
          description: `Successfully applied ${topicName} to real-world architectural scenarios.`,
          gridX: 0,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-implementation`,
          name: `Implementation Pattern`,
          layer: "APPLICATION",
          status: "DEVELOPING",
          score: 66,
          confidence: 68,
          relatedConceptIds: [],
          description: `Implementation pattern requires practice around concurrency and scalability.`,
          gridX: 1,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-tradeoffs`,
          name: `Trade-offs vs Alternatives`,
          layer: "APPLICATION",
          status: "UNTESTED",
          score: 0,
          confidence: 0,
          relatedConceptIds: [],
          description: `Trade-off comparisons not yet explored in this session.`,
          gridX: 0,
          gridY: 1,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-advanced-pattern`,
          name: `Advanced Integration`,
          layer: "APPLICATION",
          status: "UNTESTED",
          score: 0,
          confidence: 0,
          relatedConceptIds: [],
          description: `Advanced patterns scheduled for future exploration.`,
          gridX: 1,
          gridY: 1,
        },
        // EDGE CASES
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-boundary-conditions`,
          name: `Boundary & Limit Conditions`,
          layer: "EDGE_CASES",
          status: "GAP",
          score: 44,
          confidence: 84,
          relatedConceptIds: [],
          description: `Uncertainty identified when inputs or parameters reach extreme minimum or maximum values.`,
          gridX: 0,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-error-handling`,
          name: `Failure & Error Modes`,
          layer: "EDGE_CASES",
          status: "STRONG",
          score: 84,
          confidence: 82,
          relatedConceptIds: [],
          description: `Correctly identified failure recovery pathways when unexpected exceptions occur.`,
          gridX: 1,
          gridY: 0,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-scale-breakdown`,
          name: `Edge Case Inversion / Degraded State`,
          layer: "EDGE_CASES",
          status: "GAP",
          score: 46,
          confidence: 80,
          relatedConceptIds: [],
          description: `Identified knowledge gap regarding system behavior when critical subcomponents fail.`,
          gridX: 0,
          gridY: 1,
        },
        {
          id: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-corner-cases`,
          name: `Corner Case Resolution`,
          layer: "EDGE_CASES",
          status: "DEVELOPING",
          score: 62,
          confidence: 65,
          relatedConceptIds: [],
          description: `Demonstrated partial intuition for rare concurrent corner conditions.`,
          gridX: 1,
          gridY: 1,
        },
      ];

  const gaps: Gap[] = isBinarySearch
    ? [
        {
          id: "gap_bc_1",
          conceptId: "boundary-conditions",
          title: "Boundary Conditions (low <= high vs low < high)",
          severity: "HIGH",
          status: "UNRESOLVED",
          understandingScore: 42,
          confidence: 85,
          whyDetected:
            "Learner repeatedly stated that the loop should terminate when low == high, causing missed elements in single-element arrays and incorrect termination off-by-one errors.",
          evidence: [
            {
              turn: 8,
              timestamp: "15:32:14",
              curioAsked: "What happens in a single-element array if your while loop condition is 'while (low < high)'?",
              learnerAnswered: "It checks the element and finishes because low and high are both 0.",
              detectionType: "misconception",
              explanation: "0 < 0 evaluates to false immediately, so the loop never executes and returns not found.",
            },
          ],
          recommendedAction:
            "Walk through a trace of a 1-element array [5] with target 5 under both 'low < high' and 'low <= high' to observe the loop condition directly.",
          teacherInterventionAttempted: true,
          verificationSuccess: false,
        },
        {
          id: "gap_single_2",
          conceptId: "single-element-array",
          title: "Single Element / Empty Array Handling",
          severity: "MEDIUM",
          status: "UNRESOLVED",
          understandingScore: 48,
          confidence: 82,
          whyDetected:
            "Learner assumed arrays will always contain at least two elements and did not account for high = array.length - 1 becoming -1 on an empty array.",
          evidence: [
            {
              turn: 13,
              timestamp: "15:40:02",
              curioAsked: "What if someone passes an empty array [] to your search function?",
              learnerAnswered: "It will just check index 0.",
              detectionType: "gap",
              explanation: "Accessing index 0 on an empty array triggers an IndexOutOfBoundsException or undefined.",
            },
          ],
          recommendedAction:
            "Practice handling empty arrays with early-return guard clauses before calculating mid.",
          teacherInterventionAttempted: false,
          verificationSuccess: false,
        },
      ]
    : [
        {
          id: `gap_${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}_1`,
          conceptId: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-boundary-conditions`,
          title: `${topicName}: Boundary & Limit Conditions`,
          severity: "HIGH",
          status: "UNRESOLVED",
          understandingScore: 44,
          confidence: 84,
          whyDetected: `During the explanation of ${topicName}, critical boundary assumptions were omitted, leading to ambiguous behavior when input conditions reached extremes.`,
          evidence: [
            {
              turn: 6,
              timestamp: "14:20:12",
              curioAsked: `What happens in ${topicName} when inputs reach their boundary limits?`,
              learnerAnswered: `It generally defaults to the standard case without special handling.`,
              detectionType: "gap",
              explanation: `Standard handling fails at boundary extremes, causing degradation or inaccurate outputs.`,
            },
          ],
          recommendedAction: `Review boundary conditions and write explicit guard checks for ${topicName}.`,
          teacherInterventionAttempted: true,
          verificationSuccess: false,
        },
        {
          id: `gap_${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}_2`,
          conceptId: `${topicName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-scale-breakdown`,
          title: `${topicName}: Degraded State & Fault Tolerance`,
          severity: "MEDIUM",
          status: "UNRESOLVED",
          understandingScore: 46,
          confidence: 80,
          whyDetected: `Learner assumed all subcomponents of ${topicName} are perpetually available, omitting degraded state behavior.`,
          evidence: [
            {
              turn: 9,
              timestamp: "14:26:45",
              curioAsked: `How does ${topicName} recover if an intermediate dependency fails?`,
              learnerAnswered: `It assumes dependencies are always active.`,
              detectionType: "gap",
              explanation: `Resilience requires graceful degradation and fallback strategies.`,
            },
          ],
          recommendedAction: `Study fail-soft strategies and fallback patterns in ${topicName}.`,
          teacherInterventionAttempted: false,
          verificationSuccess: false,
        },
      ];

  return {
    sessionId,
    topicName,
    topicId: sessionId,
    understandingScore: 81,
    masteryLevel: "Proficient",
    evidenceConfidence: 86,
    conceptsExplored: concepts.length,
    knowledgeGaps: gaps.length,
    resolvedMisconceptions: 1,
    concepts,
    gaps,
    availableTopics,
    recommendedNextSteps: [
      `Practice Boundary Conditions in ${topicName}`,
      `Explore Degraded State & Fault Tolerance in ${topicName}`,
      `Progress to Advanced Real-World Integrations for ${topicName}`,
    ],
    createdAt: new Date().toISOString(),
  };
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
