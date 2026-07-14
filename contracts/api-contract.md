# Curio AI - API Endpoint Contracts

This document contains the schema and payload contracts for all REST endpoints. Both frontend (`HttpCurioApi`) and backend (`FastAPI` routes) must strictly conform to this contract.

---

## Health Check
### `GET /health`
Returns the status of the API and database connectivity.

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected"
}
```

---

## Sessions
### `POST /api/v1/sessions`
Create a new learning session for a specific topic.

**Request Body**:
```json
{
  "topic": "Recursion",
  "source_type": "GENERAL",
  "document_id": null
}
```

**Response (201 Created)**:
```json
{
  "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70",
  "user_id": "00000000-0000-0000-0000-000000000000",
  "topic": "Recursion",
  "source_type": "GENERAL",
  "document_id": null,
  "status": "ACTIVE",
  "created_at": "2026-07-14T17:00:00Z",
  "last_active_at": "2026-07-14T17:00:00Z",
  "ended_at": null,
  "state": {
    "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70",
    "current_mode": "STUDENT",
    "difficulty": 1,
    "confidence": 0.0,
    "active_concept": "Core Definition",
    "current_question_id": null,
    "interrupted_question_id": null,
    "consecutive_strong_answers": 0,
    "consecutive_weak_answers": 0,
    "unresolved_misconceptions": [],
    "mastered_concepts": []
  }
}
```

---

### `GET /api/v1/sessions`
Get a summary list of all previous and active sessions.

**Response (200 OK)**:
```json
[
  {
    "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70",
    "topic": "Recursion",
    "status": "ACTIVE",
    "current_mode": "STUDENT",
    "difficulty": 1,
    "confidence": 0.0,
    "created_at": "2026-07-14T17:00:00Z",
    "last_active_at": "2026-07-14T17:00:00Z"
  }
]
```

---

### `GET /api/v1/sessions/{session_id}`
Retrieve complete detail of a specific session.

**Response (200 OK)**: (Same schema as `POST /api/v1/sessions` success response)

---

### `PATCH /api/v1/sessions/{session_id}`
Update session configurations (e.g. status or renaming).

**Request Body**:
```json
{
  "topic": "Recursion (Refined)",
  "status": "ACTIVE"
}
```

**Response (200 OK)**: (Updated session detail object)

---

### `DELETE /api/v1/sessions/{session_id}`
Delete a session and all its cascading records.

**Response (204 No Content)**

---

## Messages
### `POST /api/v1/sessions/{session_id}/messages`
Send a new user message. This evaluates the answer, steps the state machine, and generates the AI's question or response.

**Request Body**:
```json
{
  "content": "A function calls itself to solve a smaller subproblem.",
  "input_type": "TEXT"
}
```

**Response (200 OK)**:
```json
{
  "user_message": {
    "message_id": "43956417-743a-4467-bc18-974fe0fb7891",
    "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70",
    "sender": "USER",
    "content": "A function calls itself to solve a smaller subproblem.",
    "input_type": "TEXT",
    "created_at": "2026-07-14T17:01:00Z"
  },
  "ai_message": {
    "message_id": "b18f090c-be4e-4b47-ae86-5384617a2a07",
    "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70",
    "sender": "AI",
    "content": "That is correct. How does the function know when to stop calling itself?",
    "input_type": "TEXT",
    "created_at": "2026-07-14T17:01:02Z"
  },
  "evaluation": {
    "correctness": 0.8,
    "clarity": 0.9,
    "completeness": 0.6,
    "depth": 0.5,
    "relevance": 1.0,
    "stuck_probability": 0.0,
    "misconceptions": [],
    "missing_concepts": ["base case"],
    "undefined_terms": [],
    "mastered_concepts": ["recursive call"],
    "knowledge_gap": "Does not explain termination mechanism or base cases.",
    "recommended_strategy": "PROBE_MISSING_CONCEPT",
    "recommended_difficulty": 1
  },
  "decision": {
    "next_mode": "STUDENT",
    "strategy": "PROBE_MISSING_CONCEPT",
    "difficulty": 1,
    "confidence": 0.35,
    "reason": "User described recursion but missed the base case or termination criteria.",
    "active_concept": "Termination Criteria",
    "should_offer_termination": false,
    "should_restore_interrupted_question": false
  }
}
```

---

### `GET /api/v1/sessions/{session_id}/messages`
Retrieve the ordered message logs for a session.

**Response (200 OK)**:
```json
[
  {
    "message_id": "43956417-743a-4467-bc18-974fe0fb7891",
    "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70",
    "sender": "USER",
    "content": "A function calls itself to solve a smaller subproblem.",
    "input_type": "TEXT",
    "created_at": "2026-07-14T17:01:00Z"
  }
]
```

---

## Session Lifecycle Controls
### `POST /api/v1/sessions/{session_id}/pause`
Pause active session status.
**Response (200 OK)**: Status updated to `PAUSED`.

### `POST /api/v1/sessions/{session_id}/resume`
Resume session.
**Response (200 OK)**: Status updated to `ACTIVE`.

### `POST /api/v1/sessions/{session_id}/end`
Ends the session and locks it. Forces transition to `EVALUATOR` mode to compile the final session report.

**Response (200 OK)**: Status updated to `COMPLETED` and returns the session report details.

---

## Reports
### `GET /api/v1/sessions/{session_id}/report`
Fetch the detailed evaluation report. Returns `404 Not Found` if the session has not been ended/completed.

**Response (200 OK)**:
```json
{
  "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70",
  "understanding_score": 85.0,
  "mastery_level": "PROFICIENT",
  "strengths": ["Clear definition of self-invocation", "Understand stack frame concepts"],
  "high_priority_learning_gaps": ["Stack overflow risks under large limits"],
  "medium_priority_learning_gaps": ["Tail call optimization implementation details"],
  "low_priority_learning_gaps": [],
  "misconceptions_detected": ["Believed stack depth is infinite by default"],
  "concepts_mastered": ["Base Case", "Call Stack"],
  "teacher_interventions_required": 1,
  "difficulty_achieved": 3,
  "personalized_roadmap": [
    "Read about Tail Recursion Optimization",
    "Solve the Fibonacci recursive stack limit problem"
  ],
  "recommended_exercises": [
    "Rewrite factorials using iterative memoization"
  ],
  "created_at": "2026-07-14T17:10:00Z"
}
```

---

## Documents (RAG Context)
### `POST /api/v1/documents`
Upload a document (PDF or plaintext) for a session.

**Request**: Multipart/form-data with file payload.

**Response (201 Created)**:
```json
{
  "document_id": "f3303d8b-594a-4e3b-b2bc-056e30b65103",
  "filename": "ohms_law_notes.pdf",
  "file_size": 104230,
  "mime_type": "application/pdf",
  "created_at": "2026-07-14T17:05:00Z"
}
```

### `GET /api/v1/documents/{document_id}`
Retrieve document metadata.

**Response (200 OK)**: (Same structure as POST response)
