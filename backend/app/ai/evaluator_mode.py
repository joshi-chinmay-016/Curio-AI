from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import AIContext
from backend.app.schemas.report import SessionReportResponse

class EvaluatorModeHandler:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def generate_report(self, context: AIContext) -> SessionReportResponse:
        history_str = "\n".join([f"{msg.sender}: {msg.content}" for msg in context.history])

        prompt = f"""
Analyze the entire conversation log for the session on topic: '{context.topic}'.
Generate a final learning evaluation report.

Conversation history:
{history_str}

Return a structured report containing:
- understanding_score: integer from 0 to 100
- mastery_level: BEGINNER, DEVELOPING, PROFICIENT, or MASTERY
- strengths: list of strings
- high_priority_learning_gaps: list of strings
- medium_priority_learning_gaps: list of strings
- low_priority_learning_gaps: list of strings
- misconceptions_detected: list of strings
- concepts_mastered: list of strings
- teacher_interventions_required: integer count
- difficulty_achieved: integer from 1 to 5
- personalized_roadmap: list of roadmap tasks
- recommended_exercises: list of exercise tasks
"""
        report = self.provider.generate_structured(prompt, SessionReportResponse)
        # Populate session id in the response object
        report.session_id = context.session_id
        return report
