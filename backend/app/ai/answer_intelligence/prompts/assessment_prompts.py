"""
Prompts for Answer Intelligence and Structured Learning Assessment.
Guides LLM to extract claims, assess relevance, evaluate concept alignment,
identify misconceptions, and compare against expected evidence.
"""
from typing import List, Optional
from backend.app.ai.answer_intelligence.schemas import ExpectedEvidence


def build_relevance_assessment_prompt(
    user_message: str,
    question: str,
    target_concept: str,
    topic: str,
    expected_evidence: Optional[ExpectedEvidence] = None,
) -> str:
    core_components_str = ""
    if expected_evidence and expected_evidence.core_components:
        core_components_str = f"Expected Core Evidence Components: {', '.join(expected_evidence.core_components)}"

    return f"""You are an expert pedagogical evaluator assessing the semantic relevance of a learner's response.
Topic: {topic}
Target Concept: {target_concept}
Question Asked by AI: "{question}"
{core_components_str}

Learner's Response:
"{user_message}"

CRITICAL INSTRUCTIONS:
1. Determine whether the learner's response actually addresses the question and target concept.
2. DO NOT reward technically true but irrelevant statements!
   Example: Question: "What is atomicity?", Answer: "SQL is a query language" or "Java was created by James Gosling".
   This is factually true in computer science, but it does NOT answer the question. It is IRRELEVANT.
3. Classify relevance as exactly ONE of:
   - RELEVANT: Directly addresses the target question and concept.
   - PARTIALLY_RELEVANT: Touches on the concept or domain but misses the direct question focus.
   - IRRELEVANT: Completely unrelated, off-topic, nonsense, personal statement, or addressing a different concept/technology.
   - CONTRADICTORY: Directly asserts the opposite or denies the premises of the concept.
   - UNCERTAIN: Incoherent or cannot be determined.

Provide a JSON object matching:
{{
  "relevance_level": "RELEVANT" | "PARTIALLY_RELEVANT" | "IRRELEVANT" | "CONTRADICTORY" | "UNCERTAIN",
  "relevance_score": float (0.0 to 1.0),
  "reason": "Concise justification for relevance score without hidden thoughts."
}}
"""


def build_claims_and_evidence_prompt(
    user_message: str,
    target_concept: str,
    expected_evidence: ExpectedEvidence,
) -> str:
    expected_items = "\n".join(f"- {c}" for c in expected_evidence.core_components)
    common_misc = "\n".join(f"- {m}" for m in expected_evidence.common_misconceptions)

    return f"""You are an expert pedagogical evaluator analyzing learner claims and evidence.
Target Concept: {target_concept}
Learner Response: "{user_message}"

Expected Evidence:
{expected_items}

Known Misconceptions for this concept:
{common_misc if common_misc else "None specified"}

Instructions:
1. Extract atomic claims made by the learner.
2. For each claim, determine if it relates to '{target_concept}' or something unrelated.
3. Map claims to the expected evidence (SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, MISSING, UNKNOWN).
4. Identify any specific misconception: incorrect mental model (e.g. "transaction can partially succeed under atomicity").
5. Assess whether the answer contains contradictory claims.

Provide a JSON object conforming to:
{{
  "claims": [
    {{
      "text": "Extracted claim",
      "concept_id": "{target_concept}" or null,
      "claim_type": "DEFINITION" | "MECHANISM" | "FACTUAL_ASSERTION" | "EXAMPLE" | "IRRELEVANT_STATEMENT",
      "alignment_score": float (0.0 to 1.0),
      "is_factually_sound": true | false | null
    }}
  ],
  "evidence": [
    {{
      "concept_id": "{target_concept}",
      "expected_description": "Expected core component",
      "status": "SUPPORTED" | "PARTIALLY_SUPPORTED" | "CONTRADICTED" | "MISSING" | "UNKNOWN",
      "supported_by_claim": "Claim text or null",
      "contradicted_by_claim": "Claim text or null",
      "confidence": float (0.0 to 1.0)
    }}
  ],
  "misconceptions": [
    {{
      "concept_id": "{target_concept}",
      "description": "Description of incorrect mental model",
      "learner_statement": "Learner quote",
      "severity": "HIGH" | "MEDIUM" | "LOW"
    }}
  ],
  "contradictory_claims": []
}}
"""
