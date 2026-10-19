from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.session import Session, SessionState
from backend.app.schemas.session import SessionCreate, SessionUpdate, SessionStateBase
from backend.app.schemas.common import SessionStatus

class SessionRepository:
    def create(self, db: SQLAlchemySession, user_id: UUID, obj_in: SessionCreate) -> Session:
        db_session = Session(
            user_id=user_id,
            topic=obj_in.topic,
            source_type=obj_in.source_type.value,
            document_id=obj_in.document_id,
            status="ACTIVE"
        )
        db.add(db_session)
        db.flush()  # get ID

        # Create initial state
        db_state = SessionState(
            session_id=db_session.id,
            current_mode=getattr(obj_in, "current_mode", "STUDENT"),
            difficulty=getattr(obj_in, "difficulty", 1),
            confidence=getattr(obj_in, "confidence", 0.0),
            active_concept=getattr(obj_in, "active_concept", "Core Definition"),
            unresolved_misconceptions=getattr(obj_in, "unresolved_misconceptions", None) or [],
            mastered_concepts=getattr(obj_in, "mastered_concepts", None) or [],
            concept_mastery=getattr(obj_in, "concept_mastery", None) or {},
            misconception_counts=getattr(obj_in, "misconception_counts", None) or {},
            recent_strategy_history=getattr(obj_in, "recent_strategy_history", None) or [],
            mode_switch_history=getattr(obj_in, "mode_switch_history", None) or [],
            teacher_attempt_count=getattr(obj_in, "teacher_attempt_count", 0),
            teacher_intervention=getattr(obj_in, "teacher_intervention", None),
        )
        db.add(db_state)
        db.commit()
        db.refresh(db_session)
        return db_session

    def get(self, db: SQLAlchemySession, id: UUID) -> Optional[Session]:
        return db.query(Session).filter(Session.id == id).first()

    def get_by_id_and_user(self, db: SQLAlchemySession, session_id: UUID, user_id: UUID) -> Optional[Session]:
        """Retrieve a session by ID ensuring it belongs to the given user."""
        return db.query(Session).filter(Session.id == session_id, Session.user_id == user_id).first()

    def list_by_user(self, db: SQLAlchemySession, user_id: UUID) -> List[Session]:
        return db.query(Session).filter(Session.user_id == user_id).order_by(Session.created_at.desc()).all()

    def list_by_user_paginated(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[SessionStatus] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> Tuple[List[Session], int]:
        """
        List sessions for a user with pagination and optional filters.

        Args:
            db: Database session.
            user_id: Owner user ID (always enforced).
            page: Page number (1-indexed), must be >= 1.
            page_size: Items per page, capped at 100.
            status: Optional session status filter.
            created_after: Optional filter for sessions created at or after this timestamp.
            created_before: Optional filter for sessions created at or before this timestamp.

        Returns:
            Tuple of (session list for the page, total count).
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query = db.query(Session).filter(Session.user_id == user_id)

        if status is not None:
            query = query.filter(Session.status == status.value)

        if created_after is not None:
            query = query.filter(Session.created_at >= created_after)

        if created_before is not None:
            query = query.filter(Session.created_at <= created_before)

        query = query.order_by(Session.created_at.desc(), Session.id.desc())

        total = query.count()

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return items, total

    def update(self, db: SQLAlchemySession, db_session: Session, obj_in: SessionUpdate) -> Session:
        if obj_in.topic is not None:
            db_session.topic = obj_in.topic
        if obj_in.status is not None:
            db_session.status = obj_in.status.value
            if obj_in.status.value == "COMPLETED" and db_session.ended_at is None:
                from datetime import datetime, timezone
                db_session.ended_at = datetime.now(timezone.utc)
        if obj_in.source_type is not None:
            db_session.source_type = obj_in.source_type.value if hasattr(obj_in.source_type, "value") else str(obj_in.source_type)
        if "document_id" in obj_in.model_fields_set:
            db_session.document_id = obj_in.document_id
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session

    def update_by_id_and_user(
        self, db: SQLAlchemySession, session_id: UUID, user_id: UUID, obj_in: SessionUpdate
    ) -> Optional[Session]:
        """Update a session only if owned by user_id."""
        db_session = self.get_by_id_and_user(db, session_id, user_id)
        if not db_session:
            return None
        return self.update(db, db_session, obj_in)

    def update_state(self, db: SQLAlchemySession, session_id: UUID, state_in: SessionStateBase) -> SessionState:
        db_state = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if not db_state:
            db_state = SessionState(session_id=session_id)
            db.add(db_state)

        fields_set = getattr(state_in, "model_fields_set", None)
        has_fields_set = isinstance(fields_set, (set, frozenset))

        def _is_explicit(field_name: str) -> bool:
            if has_fields_set:
                return field_name in fields_set
            if isinstance(state_in, dict):
                return field_name in state_in
            val = getattr(state_in, field_name, None)
            return val is not None

        def _safe_flag_modified(instance: SessionState, key: str) -> None:
            try:
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(instance, key)
            except Exception:
                pass

        if _is_explicit("current_mode"):
            db_state.current_mode = state_in.current_mode.value if hasattr(state_in.current_mode, 'value') else str(state_in.current_mode)
        elif not has_fields_set:
            db_state.current_mode = state_in.current_mode.value if hasattr(state_in.current_mode, 'value') else str(state_in.current_mode)

        if _is_explicit("difficulty"):
            db_state.difficulty = state_in.difficulty
        elif not has_fields_set:
            db_state.difficulty = state_in.difficulty

        if _is_explicit("confidence"):
            db_state.confidence = state_in.confidence
        elif not has_fields_set:
            db_state.confidence = state_in.confidence

        if _is_explicit("active_concept"):
            db_state.active_concept = state_in.active_concept
        elif not has_fields_set:
            db_state.active_concept = state_in.active_concept

        if _is_explicit("current_question_id"):
            db_state.current_question_id = state_in.current_question_id
        elif not has_fields_set and hasattr(state_in, "current_question_id"):
            db_state.current_question_id = state_in.current_question_id

        if _is_explicit("interrupted_question_id"):
            db_state.interrupted_question_id = state_in.interrupted_question_id
        elif not has_fields_set and hasattr(state_in, "interrupted_question_id"):
            db_state.interrupted_question_id = state_in.interrupted_question_id

        if _is_explicit("consecutive_strong_answers"):
            db_state.consecutive_strong_answers = state_in.consecutive_strong_answers
        elif not has_fields_set:
            db_state.consecutive_strong_answers = state_in.consecutive_strong_answers

        if _is_explicit("consecutive_weak_answers"):
            db_state.consecutive_weak_answers = state_in.consecutive_weak_answers
        elif not has_fields_set:
            db_state.consecutive_weak_answers = state_in.consecutive_weak_answers

        if _is_explicit("unresolved_misconceptions"):
            db_state.unresolved_misconceptions = list(state_in.unresolved_misconceptions) if isinstance(state_in.unresolved_misconceptions, list) else state_in.unresolved_misconceptions
            _safe_flag_modified(db_state, "unresolved_misconceptions")
        elif not has_fields_set and getattr(state_in, "unresolved_misconceptions", None) is not None:
            db_state.unresolved_misconceptions = list(state_in.unresolved_misconceptions) if isinstance(state_in.unresolved_misconceptions, list) else state_in.unresolved_misconceptions
            _safe_flag_modified(db_state, "unresolved_misconceptions")

        if _is_explicit("mastered_concepts"):
            db_state.mastered_concepts = list(state_in.mastered_concepts) if isinstance(state_in.mastered_concepts, list) else state_in.mastered_concepts
            _safe_flag_modified(db_state, "mastered_concepts")
        elif not has_fields_set and getattr(state_in, "mastered_concepts", None) is not None:
            db_state.mastered_concepts = list(state_in.mastered_concepts) if isinstance(state_in.mastered_concepts, list) else state_in.mastered_concepts
            _safe_flag_modified(db_state, "mastered_concepts")

        # Learning persistence fields
        if _is_explicit("concept_mastery"):
            db_state.concept_mastery = dict(state_in.concept_mastery) if isinstance(state_in.concept_mastery, dict) else state_in.concept_mastery
            _safe_flag_modified(db_state, "concept_mastery")
        elif not has_fields_set and getattr(state_in, "concept_mastery", None) is not None:
            db_state.concept_mastery = dict(state_in.concept_mastery) if isinstance(state_in.concept_mastery, dict) else state_in.concept_mastery
            _safe_flag_modified(db_state, "concept_mastery")

        if _is_explicit("misconception_counts"):
            db_state.misconception_counts = dict(state_in.misconception_counts) if isinstance(state_in.misconception_counts, dict) else state_in.misconception_counts
            _safe_flag_modified(db_state, "misconception_counts")
        elif not has_fields_set and getattr(state_in, "misconception_counts", None) is not None:
            db_state.misconception_counts = dict(state_in.misconception_counts) if isinstance(state_in.misconception_counts, dict) else state_in.misconception_counts
            _safe_flag_modified(db_state, "misconception_counts")

        if _is_explicit("recent_strategy_history"):
            db_state.recent_strategy_history = list(state_in.recent_strategy_history) if isinstance(state_in.recent_strategy_history, list) else state_in.recent_strategy_history
            _safe_flag_modified(db_state, "recent_strategy_history")
        elif not has_fields_set and getattr(state_in, "recent_strategy_history", None) is not None:
            db_state.recent_strategy_history = list(state_in.recent_strategy_history) if isinstance(state_in.recent_strategy_history, list) else state_in.recent_strategy_history
            _safe_flag_modified(db_state, "recent_strategy_history")

        if _is_explicit("mode_switch_history"):
            db_state.mode_switch_history = list(state_in.mode_switch_history) if isinstance(state_in.mode_switch_history, list) else state_in.mode_switch_history
            _safe_flag_modified(db_state, "mode_switch_history")
        elif not has_fields_set and getattr(state_in, "mode_switch_history", None) is not None:
            db_state.mode_switch_history = list(state_in.mode_switch_history) if isinstance(state_in.mode_switch_history, list) else state_in.mode_switch_history
            _safe_flag_modified(db_state, "mode_switch_history")

        if hasattr(state_in, 'teacher_intervention_data') and state_in.teacher_intervention_data is not None:
            db_state.teacher_intervention_data = state_in.teacher_intervention_data
        if hasattr(state_in, 'teacher_attempt_count') and state_in.teacher_attempt_count is not None:
            db_state.teacher_attempt_count = state_in.teacher_attempt_count
        if hasattr(state_in, 'teacher_intervention') and state_in.teacher_intervention is not None:
            db_state.teacher_intervention = state_in.teacher_intervention

        db.add(db_state)
        db.commit()
        db.refresh(db_state)
        return db_state

    def delete(self, db: SQLAlchemySession, id: UUID) -> bool:
        db_session = db.query(Session).filter(Session.id == id).first()
        if db_session:
            db.delete(db_session)
            db.commit()
            return True
        return False

    def delete_by_id_and_user(self, db: SQLAlchemySession, session_id: UUID, user_id: UUID) -> bool:
        """Delete a session only if owned by user_id."""
        db_session = self.get_by_id_and_user(db, session_id, user_id)
        if db_session:
            db.delete(db_session)
            db.commit()
            return True
        return False
