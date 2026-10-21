export { CharacterStage } from "./CharacterStage";
export { CharacterRenderer } from "./CharacterRenderer";
export { CharacterTransition } from "./CharacterTransition";
export { usePerformanceEngine } from "./usePerformanceEngine";
export { useCharacterEngine, VALID_TRANSITIONS } from "./useCharacterEngine";
export { bindAnimationToLearningEngine } from "./CharacterAudioSync";

export { StudentCharacter } from "./characters/StudentCharacter";
export { TeacherCharacter } from "./characters/TeacherCharacter";
export { ProfessorCharacter } from "./characters/ProfessorCharacter";

export { Notebook } from "./props/Notebook";
export { Book } from "./props/Book";
export { Clipboard } from "./props/Clipboard";
export { ThoughtBubble } from "./props/ThoughtBubble";
export { QuestionMark } from "./props/QuestionMark";
export { CheckMark } from "./props/CheckMark";

export { studentAnimations } from "./animations/student.animations";
export { teacherAnimations } from "./animations/teacher.animations";
export { professorAnimations } from "./animations/professor.animations";

export type {
  CharacterType,
  CharacterId,
  PerformanceState,
  CharacterEngineState,
  CharacterEngineActions,
  CharacterEngine,
  CharacterComponentProps,
} from "./types";
