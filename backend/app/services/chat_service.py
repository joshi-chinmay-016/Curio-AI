from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.session_repository import SessionRepository
from backend.app.repositories.message_repository import MessageRepository
from backend.app.schemas.message import (
    MessageCreate,
    ChatTurnResponse,
    MessageResponse,
    TurnEvaluationResponse,
    LearningDecisionResponse,
)
from backend.app.schemas.session import SessionStateBase
from backend.app.schemas.common import (
    LearningMode,
    InputType as CommonInputType,
    LearningStrategy,
)
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.providers.groq_provider import GroqLLMProvider
from backend.app.ai.engine import CurioEngine
from backend.app.ai.schemas import (
    AIContext,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    InputType,
    LearningContext,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    SourceMode,
    Strategy,
    TeacherIntervention,
    TurnEvaluation as AITurnEvaluation,
)


class ChatService:
    def __init__(
        self,
        ai_engine: Optional[CurioEngine] = None,
        ai_provider: Optional[BaseAIProvider] = None,
    ):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        self.ai_provider = ai_provider or GroqLLMProvider()
        # Canonical AI Engine: ensure configured provider is passed if engine is not supplied
        self.ai_engine = ai_engine or CurioEngine(provider=self.ai_provider)

    @staticmethod
    def _normalize_input_type(raw_val: Any) -> InputType:
        """
        Safely normalize raw input type to AI InputType enum:
        - Preserve valid InputType enum values.
        - Convert string values to uppercase.
        - Fallback to InputType.TEXT only when missing or invalid.
        """
        if raw_val is None:
            return InputType.TEXT
        if isinstance(raw_val, InputType):
            return raw_val
        if hasattr(raw_val, "value"):
            raw_val = raw_val.value

        if isinstance(raw_val, str):
            norm_str = raw_val.strip().upper()
            if not norm_str:
                return InputType.TEXT
            try:
                return InputType(norm_str)
            except ValueError:
                return InputType.TEXT

        return InputType.TEXT

    @staticmethod
    def _normalize_common_input_type(raw_val: Any) -> CommonInputType:
        """
        Safely normalize raw input type to CommonInputType enum:
        - Preserve valid CommonInputType enum values.
        - Convert string values to uppercase.
        - Fallback to CommonInputType.TEXT only when missing or invalid.
        """
        if raw_val is None:
            return CommonInputType.TEXT
        if isinstance(raw_val, CommonInputType):
            return raw_val
        if hasattr(raw_val, "value"):
            raw_val = raw_val.value

        if isinstance(raw_val, str):
            norm_str = raw_val.strip().upper()
            if not norm_str:
                return CommonInputType.TEXT
            try:
                return CommonInputType(norm_str)
            except ValueError:
                return CommonInputType.TEXT

        return CommonInputType.TEXT

    @staticmethod
    def _to_ai_turn_evaluation(db_eval: Any) -> Optional[AITurnEvaluation]:
        """
        Safely maps a database TurnEvaluation model instance (or dict/mock)
        to an AI TurnEvaluation schema object.
        Guards against invalid strategy enums, bounds errors on floats/ints, and missing JSON lists.
        Returns None if mapping fails unrecoverably.
        """
        if not db_eval:
            return None

        if isinstance(db_eval, AITurnEvaluation):
            return db_eval

        if not isinstance(db_eval, dict):
            if not any(hasattr(db_eval, attr) for attr in ("message_id", "correctness", "recommended_strategy")):
                return None

        def _get(key, default=None):
            if isinstance(db_eval, dict):
                return db_eval.get(key, default)
            val = getattr(db_eval, key, default)
            if hasattr(val, "_mock_return_value") or type(val).__name__ == "MagicMock":
                return default
            return val

        def _clamp_float(v, default=0.0):
            try:
                if v is None:
                    return default
                return max(0.0, min(1.0, float(v)))
            except (ValueError, TypeError):
                return default

        def _clamp_int(v, default=1, low=1, high=5):
            try:
                if v is None:
                    return default
                return max(low, min(high, int(v)))
            except (ValueError, TypeError):
                return default

        def _safe_list(v):
            if isinstance(v, list):
                return [str(x) for x in v]
            return []

        strat_val = _get("recommended_strategy", Strategy.PROBE_WHY)
        try:
            raw_str = (strat_val.value if hasattr(strat_val, "value") else str(strat_val)).strip().upper()
            strategy = Strategy(raw_str)
        except (ValueError, KeyError, AttributeError):
            strategy = Strategy.PROBE_WHY

        kg_val = _get("knowledge_gap", None)
        knowledge_gap = str(kg_val) if kg_val is not None else None

        try:
            return AITurnEvaluation(
                correctness=_clamp_float(_get("correctness", 0.0)),
                clarity=_clamp_float(_get("clarity", 0.0)),
                completeness=_clamp_float(_get("completeness", 0.0)),
                depth=_clamp_float(_get("depth", 0.0)),
                relevance=_clamp_float(_get("relevance", 1.0), default=1.0),
                stuck_probability=_clamp_float(_get("stuck_probability", 0.0)),
                misconceptions=_safe_list(_get("misconceptions", [])),
                missing_concepts=_safe_list(_get("missing_concepts", [])),
                undefined_terms=_safe_list(_get("undefined_terms", [])),
                mastered_concepts=_safe_list(_get("mastered_concepts", [])),
                knowledge_gap=knowledge_gap,
                recommended_strategy=strategy,
                recommended_difficulty=_clamp_int(_get("recommended_difficulty", 1)),
            )
        except Exception:
            return None

    def _to_message_response(self, msg: Any) -> MessageResponse:
        """Helper to convert database message model or dict to MessageResponse."""
        msg_id = getattr(msg, "id", None) or getattr(msg, "message_id", None)
        raw_input_type = getattr(msg, "input_type", None)
        input_type_enum = self._normalize_common_input_type(raw_input_type)

        created_at_val = getattr(msg, "created_at", None) or datetime.now(timezone.utc)

        return MessageResponse(
            message_id=msg_id,
            session_id=msg.session_id,
            sender=msg.sender,
            content=msg.content,
            input_type=input_type_enum,
            created_at=created_at_val,
        )

    def get_messages(
        self, db: SQLAlchemySession, session_id: UUID, user_id: Optional[UUID] = None
    ) -> List[MessageResponse]:
        if user_id:
            db_session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
            if not db_session:
                raise ValueError(f"Active session {session_id} not found.")
        db_messages = self.message_repo.list_by_session(db, session_id)
        return [self._to_message_response(m) for m in db_messages]

    def send_message(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        message_in: MessageCreate,
        user_id: Optional[UUID] = None,
    ) -> ChatTurnResponse:
        # 1. Load Session State with ownership verification
        if user_id:
            db_session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
        else:
            db_session = self.session_repo.get(db, session_id)
        if not db_session or not db_session.state:
            raise ValueError(f"Active session {session_id} not found.")

        # 2. Persist User Message
        user_msg = self.message_repo.create_message(db, session_id, "USER", message_in)

        # 3. Compile AI Context
        db_history = self.message_repo.list_by_session(db, session_id)
        ai_history = [
            ChatMessage(
                role=Role.ASSISTANT if getattr(m, "sender", "USER") == "AI" else Role.USER,
                content=m.content,
                input_type=self._normalize_input_type(getattr(m, "input_type", None))
            ) for m in db_history
        ]

        # Resolve SourceMode from session source_type
        source_mode = SourceMode.GENERAL
        if hasattr(db_session, "source_type") and db_session.source_type:
            try:
                source_mode = SourceMode(db_session.source_type)
            except ValueError:
                source_mode = SourceMode.GENERAL

        session_info = SessionInfo(
            session_id=str(session_id),
            topic=db_session.topic,
            source_mode=source_mode
        )

        # Convert LearningMode to AI Mode explicitly
        mode_val = db_session.state.current_mode
        try:
            current_mode = Mode(mode_val.value if hasattr(mode_val, "value") else str(mode_val))
        except ValueError:
            current_mode = Mode.STUDENT

        # Question hydration: safely look up message if current_question_id is set
        current_question_obj: Optional[CurrentQuestion] = None
        target_qid = db_session.state.current_question_id
        if target_qid is not None:
            target_qid_str = str(target_qid)
            matching_q = next(
                (m for m in db_history if getattr(m, "id", None) is not None and str(m.id) == target_qid_str),
                None
            )
            if matching_q:
                current_question_obj = CurrentQuestion(
                    id=str(matching_q.id),
                    content=matching_q.content,
                    concept=db_session.state.active_concept,
                    difficulty=db_session.state.difficulty
                )

        # Interrupted question hydration: safely look up message if interrupted_question_id is set
        interrupted_question_obj: Optional[CurrentQuestion] = None
        target_int_id = db_session.state.interrupted_question_id
        if target_int_id is not None:
            target_int_id_str = str(target_int_id)
            matching_int = next(
                (m for m in db_history if getattr(m, "id", None) is not None and str(m.id) == target_int_id_str),
                None
            )
            if matching_int:
                interrupted_question_obj = CurrentQuestion(
                    id=str(matching_int.id),
                    content=matching_int.content,
                    concept=db_session.state.active_concept,
                    difficulty=db_session.state.difficulty
                )

        # Teacher Mode state hydration
        raw_attempts = getattr(db_session.state, "teacher_attempt_count", 0)
        teacher_attempt_count_val = raw_attempts if isinstance(raw_attempts, int) and not isinstance(raw_attempts, bool) else 0

        teacher_intervention_obj: Optional[TeacherIntervention] = None
        raw_intervention = getattr(db_session.state, "teacher_intervention", None)
        if isinstance(raw_intervention, TeacherIntervention):
            teacher_intervention_obj = raw_intervention
        elif isinstance(raw_intervention, dict):
            try:
                teacher_intervention_obj = TeacherIntervention(**raw_intervention)
            except Exception:
                teacher_intervention_obj = None

        current_state = SessionState(
            session_id=str(session_id),
            current_mode=current_mode,
            current_difficulty=db_session.state.difficulty,
            understanding_confidence=db_session.state.confidence,
            active_concept=db_session.state.active_concept,
            current_question=current_question_obj,
            interrupted_question=interrupted_question_obj,
            consecutive_successes=db_session.state.consecutive_strong_answers,
            consecutive_failures=db_session.state.consecutive_weak_answers,
            unresolved_misconceptions=db_session.state.unresolved_misconceptions or [],
            teacher_attempt_count=teacher_attempt_count_val,
            teacher_intervention=teacher_intervention_obj,
        )

        conversation = ConversationContext(
            recent_messages=ai_history,
            message_count=len(ai_history)
        )

        # Hydrate recent evaluations for session (up to 10 chronologically)
        raw_recent_evals = []
        if hasattr(self.message_repo, "get_recent_evaluations_by_session"):
            res_evals = self.message_repo.get_recent_evaluations_by_session(db, session_id, limit=10)
            if isinstance(res_evals, list):
                raw_recent_evals = res_evals
        recent_evaluations_list: List[AITurnEvaluation] = [
            ev_obj for raw_ev in raw_recent_evals
            if (ev_obj := self._to_ai_turn_evaluation(raw_ev)) is not None
        ]

        learning_context = LearningContext(
            mastered_concepts=db_session.state.mastered_concepts or [],
            unresolved_misconceptions=db_session.state.unresolved_misconceptions or [],
            recent_evaluations=recent_evaluations_list,
            teacher_intervention=teacher_intervention_obj,
        )

        context = AIContext(
            session=session_info,
            current_state=current_state,
            conversation=conversation,
            learning_context=learning_context
        )

        # 4. Invoke AI Engine
        ai_result: AIResult = self.ai_engine.process(context)
        evaluation = ai_result.evaluation
        decision = ai_result.decision
        response = ai_result.response
        updates = ai_result.state_updates

        # 5. Persist AI Response Message
        ai_msg = self.message_repo.create_message(
            db,
            session_id,
            "AI",
            MessageCreate(content=response.content, input_type=CommonInputType.TEXT)
        )

        # 6. Save Turn Evaluation
        turn_eval_in = TurnEvaluationResponse(
            correctness=evaluation.correctness,
            clarity=evaluation.clarity,
            completeness=evaluation.completeness,
            depth=evaluation.depth,
            relevance=evaluation.relevance,
            stuck_probability=evaluation.stuck_probability,
            misconceptions=evaluation.misconceptions,
            missing_concepts=evaluation.missing_concepts,
            undefined_terms=evaluation.undefined_terms,
            mastered_concepts=evaluation.mastered_concepts,
            knowledge_gap=evaluation.knowledge_gap,
            recommended_strategy=LearningStrategy(evaluation.recommended_strategy.value if hasattr(evaluation.recommended_strategy, "value") else str(evaluation.recommended_strategy)),
            recommended_difficulty=evaluation.recommended_difficulty
        )
        self.message_repo.create_evaluation(db, user_msg.id, turn_eval_in)

        # 7. Update Session State in DB (Merging StateUpdates with existing DB state)
        if updates.current_mode is not None:
            new_mode = LearningMode(updates.current_mode.value if hasattr(updates.current_mode, "value") else str(updates.current_mode))
        else:
            curr_m = db_session.state.current_mode
            new_mode = LearningMode(curr_m.value if hasattr(curr_m, "value") else str(curr_m))

        if updates.difficulty is not None:
            new_difficulty = updates.difficulty
        else:
            new_difficulty = db_session.state.difficulty

        if updates.confidence is not None:
            new_confidence = updates.confidence
        else:
            new_confidence = db_session.state.confidence

        if updates.active_concept is not None:
            new_active_concept = updates.active_concept
        else:
            new_active_concept = db_session.state.active_concept

        # Consecutive answer streaks
        if updates.consecutive_successes is not None:
            consecutive_strong = updates.consecutive_successes
        else:
            consecutive_strong = db_session.state.consecutive_strong_answers

        if updates.consecutive_failures is not None:
            consecutive_weak = updates.consecutive_failures
        else:
            consecutive_weak = db_session.state.consecutive_weak_answers

        # Mastered concepts: merge if updates provided, else preserve existing
        existing_mastered = db_session.state.mastered_concepts or []
        if updates.mastered_concepts is not None:
            new_mastered = list(dict.fromkeys(existing_mastered + updates.mastered_concepts))
        else:
            new_mastered = list(existing_mastered)

        # Unresolved misconceptions: merge if updates provided, else preserve existing
        existing_misconceptions = db_session.state.unresolved_misconceptions or []
        if updates.unresolved_misconceptions is not None:
            new_misconceptions = list(dict.fromkeys(existing_misconceptions + updates.unresolved_misconceptions))
        else:
            new_misconceptions = list(existing_misconceptions)

        # Question ID tracking
        current_qid = ai_msg.id
        if updates.current_question and updates.current_question.id:
            try:
                current_qid = UUID(str(updates.current_question.id))
            except (ValueError, AttributeError):
                current_qid = ai_msg.id

        # Interrupted question tracking
        if decision and decision.should_restore_interrupted_question:
            new_interrupted_qid = None
        elif updates.interrupted_question is not None:
            try:
                new_interrupted_qid = UUID(str(updates.interrupted_question.id)) if updates.interrupted_question.id else None
            except (ValueError, AttributeError):
                new_interrupted_qid = db_session.state.interrupted_question_id
        elif (db_session.state.current_mode.value if hasattr(db_session.state.current_mode, "value") else str(db_session.state.current_mode)) == "STUDENT" and new_mode == LearningMode.TEACHER:
            new_interrupted_qid = db_session.state.current_question_id
        else:
            new_interrupted_qid = db_session.state.interrupted_question_id

        # Teacher Mode attempt count and intervention tracking
        if (decision and decision.should_restore_interrupted_question) or new_mode == LearningMode.STUDENT:
            new_teacher_attempts = 0
            new_teacher_intervention = None
        else:
            # Teacher Mode active
            if updates.teacher_attempt_count is not None and isinstance(updates.teacher_attempt_count, int) and not isinstance(updates.teacher_attempt_count, bool):
                new_teacher_attempts = updates.teacher_attempt_count
            else:
                raw_attempts = getattr(db_session.state, "teacher_attempt_count", 0)
                new_teacher_attempts = raw_attempts if isinstance(raw_attempts, int) and not isinstance(raw_attempts, bool) else 0

            if updates.teacher_intervention is not None:
                if isinstance(updates.teacher_intervention, dict):
                    new_teacher_intervention = updates.teacher_intervention
                elif isinstance(updates.teacher_intervention, TeacherIntervention):
                    new_teacher_intervention = updates.teacher_intervention.model_dump()
                elif hasattr(updates.teacher_intervention, "model_dump"):
                    dumped = updates.teacher_intervention.model_dump()
                    new_teacher_intervention = dumped if isinstance(dumped, dict) else None
                else:
                    new_teacher_intervention = None
            else:
                raw_ti = getattr(db_session.state, "teacher_intervention", None)
                if isinstance(raw_ti, dict):
                    new_teacher_intervention = raw_ti
                elif isinstance(raw_ti, TeacherIntervention):
                    new_teacher_intervention = raw_ti.model_dump()
                elif hasattr(raw_ti, "model_dump"):
                    dumped = raw_ti.model_dump()
                    new_teacher_intervention = dumped if isinstance(dumped, dict) else None
                else:
                    new_teacher_intervention = None

        state_update = SessionStateBase(
            current_mode=new_mode,
            difficulty=new_difficulty,
            confidence=new_confidence,
            active_concept=new_active_concept,
            current_question_id=current_qid,
            interrupted_question_id=new_interrupted_qid,
            consecutive_strong_answers=consecutive_strong,
            consecutive_weak_answers=consecutive_weak,
            unresolved_misconceptions=new_misconceptions,
            mastered_concepts=new_mastered,
            teacher_attempt_count=new_teacher_attempts,
            teacher_intervention=new_teacher_intervention,
        )

        self.session_repo.update_state(db, session_id, state_update)

        return ChatTurnResponse(
            user_message=self._to_message_response(user_msg),
            ai_message=self._to_message_response(ai_msg),
            evaluation=turn_eval_in,
            decision=LearningDecisionResponse(
                next_mode=LearningMode(decision.next_mode.value if hasattr(decision.next_mode, "value") else str(decision.next_mode)),
                strategy=LearningStrategy(decision.strategy.value if hasattr(decision.strategy, "value") else str(decision.strategy)),
                difficulty=decision.difficulty,
                confidence=decision.confidence,
                reason=decision.reason,
                active_concept=decision.active_concept,
                should_offer_termination=decision.should_offer_termination,
                should_restore_interrupted_question=decision.should_restore_interrupted_question
            )
        )


