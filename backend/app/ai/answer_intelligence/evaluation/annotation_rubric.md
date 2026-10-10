# Answer Intelligence Ground-Truth Annotation Rubric (Milestone C)

This rubric establishes deterministic, reproducible guidelines for labeling learner responses in the Curio AI Assessment Benchmark.

---

## 1. Intent Classification Rubric

| Intent | Definition | Distinguishing Criteria |
| :--- | :--- | :--- |
| `ANSWER_ATTEMPT` | Learner makes a substantive attempt to answer the pedagogical question. | Contains factual claims, mechanisms, definitions, analogies, or examples addressing the prompt. |
| `HELP_REQUEST` | Learner expresses inability to answer or asks for guidance. | Explicitly states "I don't know", "idk", "I am stuck", "Please explain". |
| `CLARIFICATION_REQUEST` | Learner asks a scoping question about the problem parameters before answering. | Inquires about constraints (e.g., "Are edges directed or undirected?", "Does this apply to IPv4 or IPv6?"). |
| `QUESTION_ABOUT_CONCEPT` | Learner asks an exploratory conceptual question. | Asks a query about how a concept works rather than answering. |
| `ACKNOWLEDGEMENT` | Learner acknowledges pedagogical advice without providing factual evidence. | "Okay", "I understand", "Got it", "Makes sense", "Thanks". Never counts as an answer. |
| `READY_TO_CONTINUE` | Learner signals readiness to proceed to the next topic. | "I'm ready", "Let's continue", "Next question". |
| `OFF_TOPIC` | Learner talks about completely unrelated subjects (movies, food, chit-chat). | Discusses weather, lunch, pets, or hobbies unrelated to computer science. |
| `EMPTY_RESPONSE` | Empty or whitespace-only response. | Empty string, tabs, or spaces. |
| `UNCERTAIN` | Highly hesitant or speculative attempt with minimal substance. | "Maybe it has something to do with caching?". |

---

## 2. Relevance Classification Rubric

| Relevance Level | Definition | Benchmark Handling |
| :--- | :--- | :--- |
| `RELEVANT` | Response directly addresses the question, learning objective, and target concept. | Scored and assessed for correctness and evidence. |
| `PARTIALLY_RELEVANT` | Response addresses the broader topic but only tangentially connects to the active concept. | Eligible for partial evidence; cannot grant full mastery. |
| `IRRELEVANT` | Response is completely unrelated to the active concept or question. | **VETO**: Immediate redirection. Correctness is `UNASSESSABLE`. Zero mastery permitted. |
| `TECHNICALLY_TRUE_IRRELEVANT` | Response is factually true about a different CS topic, but irrelevant to the active concept. | Treated as non-relevant to the target concept. Zero mastery permitted. |
| `CONTRADICTORY` | Response contains claims that mutually refute each other. | Evaluated as `CONTRADICTORY` correctness. |

---

## 3. Correctness Classification Rubric

| Correctness Level | Definition | Evidence Requirements |
| :--- | :--- | :--- |
| `CORRECT` | Answer is factually accurate, substantively complete, and free of contradictions or misconceptions. | Fully supports the essential expected evidence components. Valid paraphrases and sound analogies qualify. |
| `PARTIALLY_CORRECT` | Answer contains factually sound claims but omits core reasoning or essential components. | At least one core component supported; no active misconceptions or contradictions. |
| `INCOMPLETE` | Answer touches upon the concept but lacks essential mechanisms or explanation. | Minimal support ratio (< 0.25). |
| `INCORRECT` | Answer makes false claims or completely misidentifies the concept mechanism. | Zero supported components. |
| `MISCONCEPTION` | Answer explicitly asserts a documented conceptual anti-pattern or false belief. | Misconception predicate asserted and not refuted. |
| `CONTRADICTORY` | Answer contains mutually exclusive or contradictory assertions within the same response. | Internal or external contradiction identified. |
| `UNASSESSABLE` | Turn is non-answer (help, off-topic, empty, acknowledgement). | No factual claim to evaluate. |

---

## 4. Completeness Classification Rubric

| Level | Coverage Ratio |
| :--- | :--- |
| `COMPLETE` | $\ge 80\%$ of expected core components supported. |
| `SUBSTANTIAL` | $50\% - 79\%$ of expected core components supported. |
| `PARTIAL` | $20\% - 49\%$ of expected core components supported. |
| `MINIMAL` | $< 20\%$ of expected core components supported. |
| `NOT_APPLICABLE` | Non-answer attempts, off-topic, or empty turns. |

---

## 5. Mastery Authorization Rubric (`MasteryGate`)

### Safety Invariants:
1. **Zero Mastery on Non-Answers**: `HELP_REQUEST`, `ACKNOWLEDGEMENT`, `OFF_TOPIC`, `EMPTY_RESPONSE` strictly yield `supports_mastery = False`.
2. **Zero Mastery on Irrelevant Responses**: Any response where relevance is `IRRELEVANT` or score $< 0.65$ strictly denies mastery.
3. **Zero Mastery on Misconceptions or Contradictions**: Blocks mastery and records pedagogical gap.
4. **Positive Mastery Requirement**: Requires `CORRECT` correctness, `relevance >= 0.65`, `confidence >= 0.60`, and verified support for core evidence items.
