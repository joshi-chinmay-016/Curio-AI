# Curio AI - Streaming (SSE) Contracts

To support instant, token-by-token feedback, the chat messaging endpoint will eventually support Server-Sent Events (SSE). This document defines the wire formats for events pushed from the server.

All streams must specify `Content-Type: text/event-stream` and `Cache-Control: no-cache`.

---

## SSE Event Types

### 1. `token`
Fired continuously as the LLM generates tokens for its explanation or question.

```
event: token
data: {"content": "Why"}

event: token
data: {"content": " does"}

event: token
data: {"content": " recursion"}
```

---

### 2. `metadata`
Fired once the turn evaluation and decision machine complete calculations (usually sent immediately or at the end of the token stream). This tells the client to update mode tags, difficulty levels, and progress bars.

```
event: metadata
data: {
  "mode": "STUDENT",
  "difficulty": 2,
  "confidence": 0.48,
  "strategy": "PROBE_MISSING_CONCEPT",
  "active_concept": "Termination Criteria"
}
```

---

### 3. `complete`
Fired at the end of a successful generation. Contains the database-persisted message UUIDs and details.

```
event: complete
data: {
  "user_message_id": "43956417-743a-4467-bc18-974fe0fb7891",
  "ai_message_id": "b18f090c-be4e-4b47-ae86-5384617a2a07",
  "session_id": "fcd23b18-b2ef-45fc-ae50-cf5273295f70"
}
```

---

### 4. `error`
Fired if an exception occurs during evaluation, decision making, or LLM generation. Allows the client to gracefully show an error boundary without breaking the chat history.

```
event: error
data: {
  "code": "AI_PROVIDER_ERROR",
  "message": "Groq client rate limit reached. Re-trying..."
}
```
