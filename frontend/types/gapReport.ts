export type MasteryLevel = "Beginner" | "Developing" | "Proficient" | "Mastery";

export type ConceptStatus =
  | "STRONG"
  | "DEVELOPING"
  | "GAP"
  | "RESOLVED"
  | "UNTESTED"
  | "MISCONCEPTION";

export type UnderstandingLayer =
  | "DEFINITION"
  | "MECHANISM"
  | "APPLICATION"
  | "EDGE_CASES";

export type GapSeverity = "LOW" | "MEDIUM" | "HIGH";

export interface ConceptCell {
  id: string;
  name: string;
  layer: UnderstandingLayer;
  status: ConceptStatus;
  score: number; // 0-100
  confidence: number; // 0-100
  relatedConceptIds: string[];
  description?: string;
  // Isometric position
  gridX?: number; // column in layer grid
  gridY?: number; // row in layer grid
}

// Alias for backward compatibility
export type ConceptAssessment = ConceptCell;

export interface EvidenceItem {
  turn: number;
  timestamp: string;
  curioAsked?: string;
  learnerAnswered?: string;
  detectionType: "misconception" | "gap" | "unclear" | "strong";
  explanation: string;
}

export interface Gap {
  id: string;
  conceptId: string;
  title: string;
  severity: GapSeverity;
  status: "UNRESOLVED" | "RESOLVED";
  understandingScore: number;
  confidence: number;
  whyDetected: string;
  evidence: EvidenceItem[];
  recommendedAction: string;
  teacherInterventionAttempted: boolean;
  verificationSuccess: boolean;
}

export interface TopicOption {
  id: string;
  name: string;
}

export interface GapReport {
  sessionId: string;
  topicName: string;
  topicId: string;
  understandingScore: number;
  masteryLevel: MasteryLevel;
  evidenceConfidence: number;
  conceptsExplored: number;
  knowledgeGaps: number;
  resolvedMisconceptions: number;
  concepts: ConceptCell[];
  gaps: Gap[];
  availableTopics: TopicOption[];
  recommendedNextSteps: string[];
  createdAt: string;
}
