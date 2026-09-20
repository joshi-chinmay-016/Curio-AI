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
from backend.app.ai.orchestrator import AIOrchestrator
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
)


class ChatService:
    def __init__(self, ai_engine: Optional[CurioEngine] = None):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        # Retain legacy provider and orchestrator for backward compatibility until migration is verified
        self.ai_provider = GroqLLMProvider()
        self.orchestrator = AIOrchestrator(self.ai_provider)
        # Canonical AI Engine
        self.ai_engine = ai_engine or CurioEngine()

    def _to_message_response(self, msg: Any) -> MessageResponse:
        """Helper to convert database message model or dict to MessageResponse."""
        msg_id = getattr(msg, "id", None) or getattr(msg, "message_id", None)
        input_type_val = getattr(msg, "input_type", "TEXT")
        if hasattr(input_type_val, "value"):
            input_type_enum = CommonInputType(input_type_val.value)
        elif isinstance(input_type_val, str):
            try:
                input_type_enum = CommonInputType(input_type_val)
            except ValueError:
                input_type_enum = CommonInputType.TEXT
        else:
            input_type_enum = CommonInputType.TEXT

        created_at_val = getattr(msg, "created_at", None) or datetime.now(timezone.utc)

        return MessageResponse(
            message_id=msg_id,
            session_id=msg.session_id,
            sender=msg.sender,
            content=msg.content,
            input_type=input_type_enum,
            created_at=created_at_val,
        )

    def get_messages(self, db: SQLAlchemySession, session_id: UUID) -> List[MessageResponse]:
        db_messages = self.message_repo.list_by_session(db, session_id)
        return [self._to_message_response(m) for m in db_messages]

    def send_message(self, db: SQLAlchemySession, session_id: UUID, message_in: MessageCreate) -> ChatTurnResponse:
        # 1. Load Session State
        db_session = self.session_repo.get(db, session_id)
        if not db_session or not db_session.state:
            raise ValueError(f"Active session {session_id} not found.")

        # 2. Persist User Message
        user_msg = self.message_repo.create_message(db, session_id, "USER", message_in)

        # 3. Compile AI Context
        db_history = self.message_repo.list_by_session(db, session_id)
        ai_history = [
            ChatMessage(
                role=Role.ASSISTANT if m.sender == "AI" else Role.USER,
                content=m.content,
                input_type=InputType(m.input_type if hasattr(m, "input_type") and m.input_type else "TEXT")
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
        if db_session.state.current_question_id:
            matching_q = next((m for m in db_history if m.id == db_session.state.current_question_id), None)
            if matching_q:
                current_question_obj = CurrentQuestion(
                    id=str(matching_q.id),
                    content=matching_q.content,
                    concept=db_session.state.active_concept,
                    difficulty=db_session.state.difficulty
                )

        # Interrupted question hydration: safely look up message if interrupted_question_id is set
        interrupted_question_obj: Optional[CurrentQuestion] = None
        if db_session.state.interrupted_question_id:
            matching_int = next((m for m in db_history if m.id == db_session.state.interrupted_question_id), None)
            if matching_int:
                interrupted_question_obj = CurrentQuestion(
                    id=str(matching_int.id),
                    content=matching_int.content,
                    concept=db_session.state.active_concept,
                    difficulty=db_session.state.difficulty
                )

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
            unresolved_misconceptions=db_session.state.unresolved_misconceptions or []
        )

        conversation = ConversationContext(
            recent_messages=ai_history,
            message_count=len(ai_history)
        )

        learning_context = LearningContext(
            mastered_concepts=db_session.state.mastered_concepts or [],
            unresolved_misconceptions=db_session.state.unresolved_misconceptions or []
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
            mastered_concepts=new_mastered
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


