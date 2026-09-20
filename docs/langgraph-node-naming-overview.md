# Overview: Resolving LangGraph Node and State-Key Naming Conflicts

## 1. Executive Summary

When constructing the internal compiled workflow for Curio AI via `build_curio_graph()`, LangGraph raised the following runtime error:

```text
ValueError: 'evaluation' is already being used as a state key
```

This error occurred because the internal node names were identical to keys declared in the `CurioGraphState` schema. This document provides an architectural overview of why the error occurred, how it was resolved while preserving the AI contracts, and the verification results.

---

## 2. Root Cause Analysis

In `backend/app/ai/graph.py`, the internal state graph schema was defined as:

```python
class CurioGraphState(TypedDict, total=False):
    """Internal LangGraph state schema for Curio AI execution."""
    context: AIContext
    evaluation: Optional[TurnEvaluation]
    decision: Optional[LearningDecision]
    response: Optional[AIResponse]
    state_updates: Optional[StateUpdates]
    result: Optional[AIResult]
```

When initializing `StateGraph(CurioGraphState)`, LangGraph creates internal state channels corresponding to each field in `CurioGraphState` (`context`, `evaluation`, `decision`, `response`, `state_updates`, `result`).

In LangGraph versions compatible with Python 3.10 and Pydantic 2.6.1 (`< 0.5.0`), `StateGraph.add_node(node, action)` performs a strict namespace collision check:

```python
if node in self.channels:
    raise ValueError(f"'{node}' is already being used as a state key")
```

Because `build_curio_graph()` registered nodes with names matching the state schema keys (`"evaluation"`, `"decision"`, and `"response"`), LangGraph threw a `ValueError` during graph construction.

---

## 3. Resolution Strategy

To adhere strictly to the principle that **LangGraph is an internal implementation detail and AI contracts are the source of truth**:

1. **Preserve the AI Contract & State Keys**:
   - The state keys (`evaluation`, `decision`, `response`, `state_updates`, `result`) in `CurioGraphState` remain unchanged.
   - External contracts (`AIContext`, `AIResult`, `TurnEvaluation`, `LearningDecision`, `AIResponse`, `SessionState`) remain untouched.
   - Placeholder node return dictionaries (`{"evaluation": ...}`, `{"decision": ..., "state_updates": ...}`, `{"response": ...}`) remain unchanged.

2. **Decouple Node Names from State Keys**:
   - Renamed graph nodes using implementation-specific names with the `run_` prefix:
     - `"evaluation"` ➔ `"run_evaluation"`
     - `"decision"` ➔ `"run_decision"`
     - `"response"` ➔ `"run_response"`

3. **Update Graph Edges**:
   - Re-routed edges to connect the renamed execution nodes:
     - `START` ➔ `"run_evaluation"` ➔ `"run_decision"` ➔ `"run_response"` ➔ `END`

---

## 4. Code Changes

### 4.1 Graph Workflow Definition ([backend/app/ai/graph.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/graph.py))

```diff
 def build_curio_graph():
     """
     Constructs and compiles the minimal LangGraph workflow for Curio AI:
-    START -> evaluation -> decision -> response -> END
+    START -> run_evaluation -> run_decision -> run_response -> END
     """
     workflow = StateGraph(CurioGraphState)
 
-    workflow.add_node("evaluation", placeholder_evaluation_node)
-    workflow.add_node("decision", placeholder_decision_node)
-    workflow.add_node("response", placeholder_response_node)
+    workflow.add_node("run_evaluation", placeholder_evaluation_node)
+    workflow.add_node("run_decision", placeholder_decision_node)
+    workflow.add_node("run_response", placeholder_response_node)
 
-    workflow.add_edge(START, "evaluation")
-    workflow.add_edge("evaluation", "decision")
-    workflow.add_edge("decision", "response")
-    workflow.add_edge("response", END)
+    workflow.add_edge(START, "run_evaluation")
+    workflow.add_edge("run_evaluation", "run_decision")
+    workflow.add_edge("run_decision", "run_response")
+    workflow.add_edge("run_response", END)
 
     return workflow.compile()
```

### 4.2 Focused Validation Test ([backend/tests/ai/test_engine.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/ai/test_engine.py))

```python
def test_curio_graph_construction():
    """Verify that build_curio_graph constructs and compiles without node/state-key collisions."""
    graph = build_curio_graph()
    assert graph is not None
```

---

## 5. Verification & Test Results

### 5.1 Direct Graph Compilation Verification
```powershell
python -c "from backend.app.ai.graph import build_curio_graph; build_curio_graph(); print('Graph construction successful')"
```
**Output**:
```text
Graph construction successful
```

### 5.2 Full Test Suite Results
```text
pytest
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-8.0.0, pluggy-1.6.0
collected 26 items

backend\tests\ai\test_decision_engine.py .........                       [ 34%]
backend\tests\ai\test_engine.py .....                                    [ 53%]
backend\tests\ai\test_schemas.py ...........                             [ 96%]
backend\tests\api\test_health.py .                                       [100%]

======================= 26 passed, 50 warnings in 1.73s =======================
```

* **Passed**: 26 / 26 tests.
* **Status**: Clean execution, 100% test pass rate, no regressions introduced.
