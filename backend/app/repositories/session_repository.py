from datetime import datetime
from typing import Any, List, Optional, Tuple
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
            concept_model=getattr(obj_in, "concept_model", None),
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

        def _get_val(field_name: str) -> Any:
            if isinstance(state_in, dict):
                return state_in.get(field_name)
            return getattr(state_in, field_name, None)

        def _safe_flag_modified(instance: SessionState, key: str) -> None:
            try:
                from sqlalchemy.orm.attributes import flag_modified
                from sqlalchemy.exc import InvalidRequestError
                flag_modified(instance, key)
            except (AttributeError, KeyError, InvalidRequestError):
                pass

        if _is_explicit("current_mode"):
            mode_val = _get_val("current_mode")
            if mode_val is not None:
                db_state.current_mode = mode_val.value if hasattr(mode_val, 'value') else str(mode_val)
        elif not has_fields_set:
            mode_val = _get_val("current_mode")
            if mode_val is not None:
                db_state.current_mode = mode_val.value if hasattr(mode_val, 'value') else str(mode_val)

        if _is_explicit("difficulty"):
            diff_val = _get_val("difficulty")
            if diff_val is not None:
                db_state.difficulty = diff_val
        elif not has_fields_set:
            diff_val = _get_val("difficulty")
            if diff_val is not None:
                db_state.difficulty = diff_val

        if _is_explicit("confidence"):
            conf_val = _get_val("confidence")
            if conf_val is not None:
                db_state.confidence = conf_val
        elif not has_fields_set:
            conf_val = _get_val("confidence")
            if conf_val is not None:
                db_state.confidence = conf_val

        if _is_explicit("active_concept"):
            ac_val = _get_val("active_concept")
            if ac_val is not None:
                db_state.active_concept = ac_val
        elif not has_fields_set:
            ac_val = _get_val("active_concept")
            if ac_val is not None:
                db_state.active_concept = ac_val

        if _is_explicit("current_question_id"):
            db_state.current_question_id = _get_val("current_question_id")
        elif not has_fields_set and (hasattr(state_in, "current_question_id") or (isinstance(state_in, dict) and "current_question_id" in state_in)):
            db_state.current_question_id = _get_val("current_question_id")

        if _is_explicit("interrupted_question_id"):
            db_state.interrupted_question_id = _get_val("interrupted_question_id")
        elif not has_fields_set and (hasattr(state_in, "interrupted_question_id") or (isinstance(state_in, dict) and "interrupted_question_id" in state_in)):
            db_state.interrupted_question_id = _get_val("interrupted_question_id")

        if _is_explicit("consecutive_strong_answers"):
            csa_val = _get_val("consecutive_strong_answers")
            if csa_val is not None:
                db_state.consecutive_strong_answers = csa_val
        elif not has_fields_set:
            csa_val = _get_val("consecutive_strong_answers")
            if csa_val is not None:
                db_state.consecutive_strong_answers = csa_val

        if _is_explicit("consecutive_weak_answers"):
            cwa_val = _get_val("consecutive_weak_answers")
            if cwa_val is not None:
                db_state.consecutive_weak_answers = cwa_val
        elif not has_fields_set:
            cwa_val = _get_val("consecutive_weak_answers")
            if cwa_val is not None:
                db_state.consecutive_weak_answers = cwa_val

        # Non-nullable collections: protect against None accidentally erasing valid state
        um_val = _get_val("unresolved_misconceptions")
        if _is_explicit("unresolved_misconceptions") and um_val is not None:
            db_state.unresolved_misconceptions = list(um_val) if isinstance(um_val, list) else um_val
            _safe_flag_modified(db_state, "unresolved_misconceptions")
        elif not has_fields_set and um_val is not None:
            db_state.unresolved_misconceptions = list(um_val) if isinstance(um_val, list) else um_val
            _safe_flag_modified(db_state, "unresolved_misconceptions")

        mc_val = _get_val("mastered_concepts")
        if _is_explicit("mastered_concepts") and mc_val is not None:
            db_state.mastered_concepts = list(mc_val) if isinstance(mc_val, list) else mc_val
            _safe_flag_modified(db_state, "mastered_concepts")
        elif not has_fields_set and mc_val is not None:
            db_state.mastered_concepts = list(mc_val) if isinstance(mc_val, list) else mc_val
            _safe_flag_modified(db_state, "mastered_concepts")

        # Learning persistence fields (all nullable=False in schema/DB)
        cm_val = _get_val("concept_mastery")
        if _is_explicit("concept_mastery") and cm_val is not None:
            db_state.concept_mastery = dict(cm_val) if isinstance(cm_val, dict) else cm_val
            _safe_flag_modified(db_state, "concept_mastery")
        elif not has_fields_set and cm_val is not None:
            db_state.concept_mastery = dict(cm_val) if isinstance(cm_val, dict) else cm_val
            _safe_flag_modified(db_state, "concept_mastery")

        misc_val = _get_val("misconception_counts")
        if _is_explicit("misconception_counts") and misc_val is not None:
            db_state.misconception_counts = dict(misc_val) if isinstance(misc_val, dict) else misc_val
            _safe_flag_modified(db_state, "misconception_counts")
        elif not has_fields_set and misc_val is not None:
            db_state.misconception_counts = dict(misc_val) if isinstance(misc_val, dict) else misc_val
            _safe_flag_modified(db_state, "misconception_counts")

        strat_val = _get_val("recent_strategy_history")
        if _is_explicit("recent_strategy_history") and strat_val is not None:
            db_state.recent_strategy_history = list(strat_val) if isinstance(strat_val, list) else strat_val
            _safe_flag_modified(db_state, "recent_strategy_history")
        elif not has_fields_set and strat_val is not None:
            db_state.recent_strategy_history = list(strat_val) if isinstance(strat_val, list) else strat_val
            _safe_flag_modified(db_state, "recent_strategy_history")

        mode_sw_val = _get_val("mode_switch_history")
        if _is_explicit("mode_switch_history") and mode_sw_val is not None:
            db_state.mode_switch_history = list(mode_sw_val) if isinstance(mode_sw_val, list) else mode_sw_val
            _safe_flag_modified(db_state, "mode_switch_history")
        elif not has_fields_set and mode_sw_val is not None:
            db_state.mode_switch_history = list(mode_sw_val) if isinstance(mode_sw_val, list) else mode_sw_val
            _safe_flag_modified(db_state, "mode_switch_history")

        model_val = _get_val("concept_model")
        if _is_explicit("concept_model"):
            if model_val is not None:
                db_state.concept_model = dict(model_val) if isinstance(model_val, dict) else model_val
                _safe_flag_modified(db_state, "concept_model")
        elif not has_fields_set and model_val is not None:
            db_state.concept_model = dict(model_val) if isinstance(model_val, dict) else model_val
            _safe_flag_modified(db_state, "concept_model")

        if hasattr(state_in, 'teacher_intervention_data') and state_in.teacher_intervention_data is not None:
            db_state.teacher_intervention_data = state_in.teacher_intervention_data
        elif isinstance(state_in, dict) and state_in.get("teacher_intervention_data") is not None:
            db_state.teacher_intervention_data = state_in["teacher_intervention_data"]

        if hasattr(state_in, 'teacher_attempt_count') and state_in.teacher_attempt_count is not None:
            db_state.teacher_attempt_count = state_in.teacher_attempt_count
        elif isinstance(state_in, dict) and state_in.get("teacher_attempt_count") is not None:
            db_state.teacher_attempt_count = state_in["teacher_attempt_count"]

        if hasattr(state_in, 'teacher_intervention') and state_in.teacher_intervention is not None:
            db_state.teacher_intervention = state_in.teacher_intervention
        elif isinstance(state_in, dict) and state_in.get("teacher_intervention") is not None:
            db_state.teacher_intervention = state_in["teacher_intervention"]

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
