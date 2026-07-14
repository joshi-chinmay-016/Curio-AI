# Database Schema & Persistence Design

This document details the database models used for Curio AI sessions, messages, and evaluations.

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : "creates"
    SESSIONS ||--o{ MESSAGES : "contains"
    SESSIONS ||--|| SESSION_STATES : "tracks state"
    SESSIONS ||--|| SESSION_REPORTS : "evaluates"
    MESSAGES ||--o| TURN_EVALUATIONS : "evaluates user response"

    USERS {
        uuid id PK
        string email
        timestamp created_at
    }

    SESSIONS {
        uuid id PK
        uuid user_id FK
        string topic
        string source_type
        uuid document_id FK
        string status
        timestamp created_at
        timestamp last_active_at
    }

    SESSION_STATES {
        uuid session_id PK, FK
        string current_mode
        int difficulty
        float confidence
        string active_concept
        uuid current_question_id FK
        uuid interrupted_question_id FK
        int consecutive_strong_answers
        int consecutive_weak_answers
        jsonb unresolved_misconceptions
        jsonb mastered_concepts
    }

    MESSAGES {
        uuid id PK
        uuid session_id FK
        string sender
        text content
        string input_type
        timestamp created_at
    }

    TURN_EVALUATIONS {
        uuid message_id PK, FK
        float correctness
        float clarity
        float completeness
        float depth
        float relevance
        float stuck_probability
        jsonb misconceptions
        jsonb missing_concepts
        jsonb undefined_terms
        jsonb mastered_concepts
        text knowledge_gap
        string recommended_strategy
        int recommended_difficulty
    }
```

## Key Databases Practices

1. **UUID Keys**: All models use UUIDv4 for IDs. This makes it safe to reference IDs on the client side before they are fully persisted, facilitating mock compatibility.
2. **Strict Message Sequencing**: Messages are ordered using a timestamp or an autoincrementing integer. We index `session_id` and `created_at` on the `messages` table to ensure fast history retrieval.
3. **JSONB Serialization**: Lists (such as `misconceptions` or `mastered_concepts`) are stored in PostgreSQL using `JSONB` columns, avoiding the overhead of creating separate child tables for simple array attributes in the MVP.
4. **Foreign Key Constraints**: Delete actions on sessions cascade down to messages, session states, turn evaluations, and reports.
