# AI MILESTONE C: ASSESSMENT RELIABILITY REPOSITORY AUDIT & BASELINE

## 1. Executive Summary & Git State
- **Branch**: `feature/ai`
- **Working Tree**: Clean, ahead of `origin/feature/ai` by 1 commit.
- **Goal**: Implement AI Milestone C (Assessment Reliability, Evidence-Based Correctness & Mastery Safety).
- **Primary Objective**: Distinguish fluent language from genuine understanding, eradicate false mastery, calibrate confidence, improve correctness and completeness assessment, and fortify Student and Teacher modes.

## 2. Currently Selected Architecture & Provider Configuration
- **Active Provider**: `HybridSemanticProvider` (configured in `AssessmentAggregator.__init__` with fallback to `LocalAssessmentProvider`).
- **Core Models**:
  - `sentence-transformers/all-MiniLM-L6-v2` locally cached in Hugging Face hub (`~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2`).
  - Local lexical tokenizer, negation parser, and deterministic pattern matcher.
- **Safety Gate**: `MasteryGate` acts as sole authority authorizing mastery progression.

## 3. Baseline Metric Reproduction (105 Machine-Labeled Benchmark Cases)
Evaluation executed via `backend/app/ai/answer_intelligence/evaluation/run_comparison.py`:

| Metric | Baseline Local | Semantic Embedding (`all-MiniLM-L6-v2`) | Hybrid Semantic (Active Baseline) |
| :--- | :--- | :--- | :--- |
| **Total Cases** | 105 | 105 | 105 |
| **Intent Accuracy** | 91.40% | 91.40% | 91.40% |
| **Relevance Accuracy** | 80.00% | 84.80% | **86.70%** |
| **Correctness Accuracy** | 51.40% | 33.30% | **38.10%** |
| **Completeness Accuracy** | 45.70% | 45.70% | **46.70%** |
| **Misconception Precision** | 0.00% | 35.70% | **33.30%** |
| **Misconception Recall** | 0.00% | 47.60% | **42.90%** |
| **Mastery Precision** | 74.40% | 50.00% | **60.00%** |
| **Mastery Recall** | 60.40% | 12.50% | **31.20%** |
| **FALSE MASTERY RATE** | 17.54% | 10.53% | **17.54%** |
| **False Rejection Rate** | 39.58% | 87.50% | **68.75%** |
| **Irrelevant Acceptance Rate** | 33.33% | 16.67% | **33.33%** |
| **Abstention Rate** | 0.00% | 8.60% | **1.90%** |
| **Average Latency** | 1.41 ms | 282.53 ms | **286.22 ms** |
| **P95 Latency** | 2.42 ms | 466.68 ms | **520.39 ms** |
| **Cold Start** | 2.83 ms | 435.59 ms | **283.57 ms** |

## 4. Test Suite Audit & Environmental Limitations
- **AI Test Suite (`backend/tests/ai`)**: 297 passed in 95.63s (100% pass rate).
- **Core Test Suite (`backend/tests/core`)**: 20 passed in 6.76s (100% pass rate).
- **PostgreSQL / Integration Tests**: Require dedicated test container on `localhost:5433` (`curio_test_db`). Docker Desktop daemon is currently not running in the local Windows environment, causing live DB integration connection errors. AI assessment and unit suites operate completely standalone and offline without database dependencies.

## 5. Phase C1 Error Analysis (Main Failure Modes)
Detailed analysis across all 105 benchmark cases revealed the following core failure modes:

1. **False Mastery on Partial and Misconception Answers (10 cases, 17.54% FMR)**:
   - In answers like `dbms_02_atomicity_misconception_partial_commit` and `os_14_process_vs_thread_misconception`, the misconception was not detected. Dense embedding similarity against the concept description reached 0.70+, granting false positive mastery.
   - Partial answers (`dbms_08`, `ds_37`, `algo_44`, `oop_55`, `py_66`) were elevated to full `CORRECT` because 1 supported component exceeded the loose 0.70 ratio calculation.
2. **False Misconceptions Flagged on Correct Answers (18 cases)**:
   - In `os_11`, `net_21`, `net_30`, `ds_31`, `ds_36`, correct answers discussing technical concepts (e.g. paging and RAM, hash table collisions) shared tokens with common misconception descriptions (e.g. "hash tables have zero collisions"). `SemanticEmbeddingProvider` triggered misconception flags at `sim >= 0.50` with single keyword overlap, flipping 18 valid answers to `MISCONCEPTION` and causing severe false rejections (68.75%).
3. **Misconceptions Not Detected (12 cases, 42.90% recall)**:
   - Symmetric cosine similarity fails on asymmetric conceptual refutations and subtle predicate reversals (e.g., "commits whatever succeeded and cancels the broken query").
4. **Analogy and Paraphrase Rejection**:
   - Students explaining concepts with valid analogies (`dbms_03_atomicity_analogy`, `os_13_deadlock_circular_wait_analogy`, `ds_38_trie_prefix_search_analogy`) were rejected as `INCORRECT` because lexical overlap was low even though semantic alignment was high.
5. **Contradictory Claims Ignored**:
   - Mixed answers containing both correct statements and contradictory claims (`ml_104`, `js_80`, `dist_98`) were graded as fully correct because positive matches masked internal contradictions.

## 6. End-to-End Assessment Pipeline Trace
```
Learner Answer
  ↓
Turn & Intent Classification (Fast lexical + deterministic intent guards)
  ↓
Semantic Relevance Evaluation (Hybrid lexical overlap + dense vector check, veto if < 0.20)
  ↓
Claim Extraction (Sentence segmentation + semantic/lexical alignment)
  ↓
Concept Alignment (Maximum of lexical overlap and dense embedding score)
  ↓
Evidence Matching (Asymmetric claim-to-evidence support and contradiction check)
  ↓
Correctness Evaluation (Requires substantive claim-level support; blocks contradictions)
  ↓
Completeness Evaluation (Measures core component coverage)
  ↓
Misconception Detection (Checks asymmetric assertion of known anti-patterns; respects refutations)
  ↓
Confidence & Abstention Calibration (Abstains on ambiguous, out-of-distribution, or conflicted inputs)
  ↓
Canonical LearningAssessment
  ↓
Authoritative MasteryGate (Deterministic barrier protecting Learner Model)
  ↓
Pedagogical Nodes (Student Mode / Teacher Mode)
  ↓
AIResult & Backend State Updates
```
