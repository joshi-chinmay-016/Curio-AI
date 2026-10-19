import {
  CharacterPerformanceEngine,
  LearningEngineEvents,
  AssessmentResult,
} from "@/types/performanceEngine";

/**
 * Binds CharacterPerformanceEngine to conversational audio & learning engine events.
 * Returns an unbind cleanup function.
 */
export function bindAnimationToLearningEngine(
  engine: CharacterPerformanceEngine,
  events: LearningEngineEvents
): () => void {
  const origRecordStart = events.onRecordStart;
  const origRecordStop = events.onRecordStop;
  const origSpeechStart = events.onSpeechStart;
  const origSpeechEnd = events.onSpeechEnd;
  const origSpeechError = events.onSpeechError;
  const origAssessmentResult = events.onAssessmentResult;
  const origTeacherIntervention = events.onTeacherIntervention;
  const origTeacherComplete = events.onTeacherComplete;
  const origSessionEnd = events.onSessionEnd;

  events.onRecordStart = () => {
    engine.transition("LISTENING_ACTIVE");
    origRecordStart?.();
  };

  events.onRecordStop = () => {
    // When recording stops, character transitions to THINKING to process what was heard
    engine.transition("THINKING");
    origRecordStop?.();
  };

  events.onSpeechStart = () => {
    engine.transition("SPEAKING");
    origSpeechStart?.();
  };

  events.onSpeechEnd = () => {
    engine.transition("IDLE");
    origSpeechEnd?.();
  };

  events.onSpeechError = () => {
    // Critical safety: never leave character in SPEAKING if audio fails!
    engine.interrupt("error");
    origSpeechError?.();
  };

  events.onAssessmentResult = (result: AssessmentResult) => {
    if (result.isPositive) {
      engine.transition("REACTING_POSITIVE");
    } else if (result.hasMisconception) {
      engine.transition("REACTING_CONFUSED");
    } else if (engine.activeCharacter === "PROFESSOR" && result.isWeak) {
      engine.transition("REACTING_STRICT");
    } else {
      if (engine.activeCharacter === "PROFESSOR") {
        engine.transition("MARKING");
      } else {
        engine.transition("TAKING_NOTES");
      }
    }
    origAssessmentResult?.(result);
  };

  events.onTeacherIntervention = () => {
    engine.swapCharacter("TEACHER");
    origTeacherIntervention?.();
  };

  events.onTeacherComplete = () => {
    engine.swapCharacter("STUDENT");
    origTeacherComplete?.();
  };

  events.onSessionEnd = (reason) => {
    if (reason === "unanswered_threshold" && engine.activeCharacter === "PROFESSOR") {
      engine.transition("REACTING_GRUMPY");
    } else {
      engine.transition("EXITING");
    }
    origSessionEnd?.(reason);
  };

  return () => {
    events.onRecordStart = origRecordStart;
    events.onRecordStop = origRecordStop;
    events.onSpeechStart = origSpeechStart;
    events.onSpeechEnd = origSpeechEnd;
    events.onSpeechError = origSpeechError;
    events.onAssessmentResult = origAssessmentResult;
    events.onTeacherIntervention = origTeacherIntervention;
    events.onTeacherComplete = origTeacherComplete;
    events.onSessionEnd = origSessionEnd;
  };
}
