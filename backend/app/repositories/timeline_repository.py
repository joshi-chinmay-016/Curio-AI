from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.schemas.timeline import SUPPORTED_EVENT_TYPES


class TimelineRepository:
    def _build_base_query(self) -> str:
        """
        Build the base UNION ALL query for all timeline event sources.
        Returns a CTE that can be filtered, ordered, and paginated.
        All sources enforce ownership via user_id inside SQL.
        """
        return """
        WITH all_events AS (
            -- 1. session_created
            SELECT
                'session_created' AS event_type,
                s.created_at AS timestamp,
                s.id AS session_id,
                CAST(NULL AS uuid) AS message_id,
                s.id AS entity_id,
                jsonb_build_object('topic', s.topic, 'source_type', s.source_type) AS metadata
            FROM sessions s
            WHERE s.user_id = CAST(:user_id AS uuid)

            UNION ALL

            -- 2. user_message
            SELECT
                'user_message' AS event_type,
                m.created_at AS timestamp,
                m.session_id AS session_id,
                m.id AS message_id,
                m.id AS entity_id,
                jsonb_build_object('input_type', m.input_type, 'content', left(coalesce(m.content, ''), 500)) AS metadata
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            WHERE s.user_id = CAST(:user_id AS uuid)
              AND m.sender = 'USER'

            UNION ALL

            -- 3. evaluation
            SELECT
                'evaluation' AS event_type,
                m.created_at AS timestamp,
                m.session_id AS session_id,
                m.id AS message_id,
                e.message_id AS entity_id,
                jsonb_build_object(
                    'correctness', e.correctness,
                    'recommended_strategy', e.recommended_strategy,
                    'recommended_difficulty', e.recommended_difficulty
                ) AS metadata
            FROM messages m
            JOIN turn_evaluations e ON e.message_id = m.id
            JOIN sessions s ON s.id = m.session_id
            WHERE s.user_id = CAST(:user_id AS uuid)
              AND m.sender = 'USER'

            UNION ALL

            -- 4. turn_assessment
            SELECT
                'turn_assessment' AS event_type,
                a.created_at AS timestamp,
                a.session_id AS session_id,
                a.message_id AS message_id,
                a.id AS entity_id,
                jsonb_build_object(
                    'has_learning_assessment', (a.learning_assessment IS NOT NULL AND jsonb_typeof(CAST(a.learning_assessment AS jsonb)) != 'null'),
                    'has_turn_interpretation', (a.turn_interpretation IS NOT NULL AND jsonb_typeof(CAST(a.turn_interpretation AS jsonb)) != 'null'),
                    'has_learning_objective', (a.learning_objective IS NOT NULL AND jsonb_typeof(CAST(a.learning_objective AS jsonb)) != 'null'),
                    'has_question_specification', (a.question_specification IS NOT NULL AND jsonb_typeof(CAST(a.question_specification AS jsonb)) != 'null')
                ) AS metadata
            FROM turn_assessments a
            WHERE a.user_id = CAST(:user_id AS uuid)

            UNION ALL

            -- 5. teacher_intervention
            SELECT
                'teacher_intervention' AS event_type,
                i.created_at AS timestamp,
                i.session_id AS session_id,
                CAST(NULL AS uuid) AS message_id,
                i.id AS entity_id,
                jsonb_build_object(
                    'intervention_type', i.intervention_type,
                    'gap', left(coalesce(i.gap, ''), 500),
                    'attempt_count', i.attempt_count,
                    'verification_passed', i.verification_passed
                ) AS metadata
            FROM teacher_intervention_logs i
            WHERE i.user_id = CAST(:user_id AS uuid)

            UNION ALL

            -- 6. report_generated
            SELECT
                'report_generated' AS event_type,
                r.created_at AS timestamp,
                r.session_id AS session_id,
                CAST(NULL AS uuid) AS message_id,
                r.session_id AS entity_id,
                jsonb_build_object(
                    'understanding_score', r.understanding_score,
                    'mastery_level', r.mastery_level,
                    'concepts_mastered_count', CASE
                        WHEN r.concepts_mastered IS NOT NULL AND jsonb_typeof(CAST(r.concepts_mastered AS jsonb)) = 'array'
                        THEN jsonb_array_length(CAST(r.concepts_mastered AS jsonb))
                        ELSE 0
                    END
                ) AS metadata
            FROM session_reports r
            JOIN sessions s ON s.id = r.session_id
            WHERE s.user_id = CAST(:user_id AS uuid)

            UNION ALL

            -- 7. session_ended
            SELECT
                'session_ended' AS event_type,
                s.ended_at AS timestamp,
                s.id AS session_id,
                CAST(NULL AS uuid) AS message_id,
                s.id AS entity_id,
                jsonb_build_object('status', s.status) AS metadata
            FROM sessions s
            WHERE s.user_id = CAST(:user_id AS uuid)
              AND s.ended_at IS NOT NULL
        )
        """

    def _build_filtered_query(
        self,
        session_id: Optional[UUID],
        event_types: Optional[List[str]],
        start: Optional[datetime],
        end: Optional[datetime],
        include_pagination: bool = False,
    ) -> Tuple[str, dict]:
        """
        Build the filtered query with parameterized values.
        Returns (query_string, params_dict).
        """
        base_cte = self._build_base_query()
        where_clauses = []
        params = {"user_id": None}

        if session_id:
            where_clauses.append("session_id = CAST(:session_id AS uuid)")
            params["session_id"] = str(session_id)

        if event_types:
            validated = [et for et in event_types if et in SUPPORTED_EVENT_TYPES]
            if validated:
                placeholders = ", ".join([f":event_type_{i}" for i in range(len(validated))])
                where_clauses.append(f"event_type IN ({placeholders})")
                for i, et in enumerate(validated):
                    params[f"event_type_{i}"] = et
            else:
                where_clauses.append("FALSE")

        if start:
            where_clauses.append("timestamp >= :start")
            params["start"] = start

        if end:
            where_clauses.append("timestamp <= :end")
            params["end"] = end

        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)

        if include_pagination:
            query = f"""
            {base_cte}
            SELECT event_type, timestamp, session_id, message_id, entity_id, metadata
            FROM all_events
            {where_sql}
            ORDER BY timestamp ASC, entity_id ASC NULLS LAST, event_type ASC
            LIMIT :limit OFFSET :offset
            """
            params["limit"] = None
            params["offset"] = None
        else:
            query = f"""
            {base_cte}
            SELECT COUNT(*) FROM all_events
            {where_sql}
            """

        return query, params

    def get_timeline(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        session_id: Optional[UUID] = None,
        event_types: Optional[List[str]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Tuple[List, int]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query, params = self._build_filtered_query(
            session_id=session_id,
            event_types=event_types,
            start=start,
            end=end,
            include_pagination=True,
        )
        params["user_id"] = str(user_id)
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        result = db.execute(text(query), params).fetchall()

        # Count query
        count_query, count_params = self._build_filtered_query(
            session_id=session_id,
            event_types=event_types,
            start=start,
            end=end,
            include_pagination=False,
        )
        count_params["user_id"] = str(user_id)
        total = db.execute(text(count_query), count_params).scalar()

        return result, total or 0

    def get_timeline_count(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        session_id: Optional[UUID] = None,
        event_types: Optional[List[str]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        query, params = self._build_filtered_query(
            session_id=session_id,
            event_types=event_types,
            start=start,
            end=end,
            include_pagination=False,
        )
        params["user_id"] = str(user_id)
        return db.execute(text(query), params).scalar() or 0