from typing import List
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.session_repository import SessionRepository
from backend.app.repositories.message_repository import MessageRepository
from backend.app.schemas.message import MessageCreate, ChatTurnResponse, MessageResponse, TurnEvaluationResponse, LearningDecisionResponse
from backend.app.schemas.session import SessionStateBase
from backend.app.schemas.common import LearningMode, InputType, LearningStrategy
from backend.app.ai.orchestrator import AIOrchestrator
from backend.app.ai.providers.groq_provider import GroqLLMProvider
from backend.app.ai.schemas import AIContext, ChatMessage

class ChatService:
    def __init__(self):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        # Initialize Groq LLM provider (will fall back to Mock if no API key)
        self.ai_provider = GroqLLMProvider()
        self.orchestrator = AIOrchestrator(self.ai_provider)

    def get_messages(self, db: SQLAlchemySession, session_id: UUID) -> List[MessageResponse]:
        db_messages = self.message_repo.list_by_session(db, session_id)
        return [MessageResponse.model_validate(m) for m in db_messages]

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
                sender=m.sender,
                content=m.content,
                input_type=InputType(m.input_type)
            ) for m in db_history
        ]

        active_question = ""
        if len(db_history) > 1:
            # Finding last question asked by AI
            ai_messages = [m for m in db_history if m.sender == "AI"]
            if ai_messages:
                active_question = ai_messages[-1].content

        context = AIContext(
            session_id=session_id,
            topic=db_session.topic,
            current_mode=LearningMode(db_session.state.current_mode),
            difficulty=db_session.state.difficulty,
            active_concept=db_session.state.active_concept,
            current_question=active_question,
            interrupted_question=None,  # Handled in decision if restored
            document_context=None,
            history=ai_history
        )

        # 4. Invoke AI Engine
        ai_response = self.orchestrator.process_turn(
            context,
            consecutive_strong=db_session.state.consecutive_strong_answers,
            consecutive_weak=db_session.state.consecutive_weak_answers
        )

        # Extract structured outputs
        evaluation_data = ai_response.metadata["evaluation"]
        decision_data = ai_response.metadata["decision"]

        # 5. Persist AI Response Message
        ai_msg = self.message_repo.create_message(
            db,
            session_id,
            "AI",
            MessageCreate(content=ai_response.content, input_type=InputType.TEXT)
        )

        # 6. Save Turn Evaluation
        turn_eval = self.message_repo.create_evaluation(
            db,
            user_msg.id,
            TurnEvaluationResponse(
                correctness=evaluation_data["correctness"],
                clarity=evaluation_data["clarity"],
                completeness=evaluation_data["completeness"],
                depth=evaluation_data["depth"],
                relevance=evaluation_data["relevance"],
                stuck_probability=evaluation_data["stuck_probability"],
                misconceptions=evaluation_data["misconceptions"],
                missing_concepts=evaluation_data["missing_concepts"],
                undefined_terms=evaluation_data["undefined_terms"],
                mastered_concepts=evaluation_data["mastered_concepts"],
                knowledge_gap=evaluation_data["knowledge_gap"],
                recommended_strategy=LearningStrategy(evaluation_data["recommended_strategy"]),
                recommended_difficulty=evaluation_data["recommended_difficulty"]
            )
        )

        # 7. Update Session State in DB
        consecutive_strong = db_session.state.consecutive_strong_answers
        consecutive_weak = db_session.state.consecutive_weak_answers
        if evaluation_data["correctness"] > 0.7:
            consecutive_strong += 1
            consecutive_weak = 0
        else:
            consecutive_weak += 1
            consecutive_strong = 0

        # Maintain list of mastered concepts
        new_mastered = list(set(db_session.state.mastered_concepts + evaluation_data["mastered_concepts"]))

        # Build state updates
        state_update = SessionStateBase(
            current_mode=LearningMode(decision_data["next_mode"]),
            difficulty=decision_data["difficulty"],
            confidence=decision_data["confidence"],
            active_concept=decision_data["active_concept"],
            current_question_id=ai_msg.id,
            interrupted_question_id=db_session.state.interrupted_question_id,
            consecutive_strong_answers=consecutive_strong,
            consecutive_weak_answers=consecutive_weak,
            unresolved_misconceptions=list(set(db_session.state.unresolved_misconceptions + evaluation_data["misconceptions"])),
            mastered_concepts=new_mastered
        )

        # If switching from student to teacher, record the interrupted question ID
        if db_session.state.current_mode == "STUDENT" and decision_data["next_mode"] == "TEACHER":
            # Store user_msg or previous AI question as interrupted
            state_update.interrupted_question_id = db_session.state.current_question_id

        # If switching back to student, clear interrupted question
        if decision_data["should_restore_interrupted_question"]:
            state_update.interrupted_question_id = None

        self.session_repo.update_state(db, session_id, state_update)

        return ChatTurnResponse(
            user_message=MessageResponse.model_validate(user_msg),
            ai_message=MessageResponse.model_validate(ai_msg),
            evaluation=TurnEvaluationResponse.model_validate(turn_eval),
            decision=LearningDecisionResponse(
                next_mode=LearningMode(decision_data["next_mode"]),
                strategy=LearningStrategy(decision_data["strategy"]),
                difficulty=decision_data["difficulty"],
                confidence=decision_data["confidence"],
                reason=decision_data["reason"],
                active_concept=decision_data["active_concept"],
                should_offer_termination=decision_data["should_offer_termination"],
                should_restore_interrupted_question=decision_data["should_restore_interrupted_question"]
            )
        )
