export type AppTheme = "light" | "dark" | "system";

export type FeynmanRigorLevel = "gentle" | "socratic" | "rigorous";
export type EvaluationStrictness = "lenient" | "standard" | "unforgiving";
export type CharacterAvatarId = "STUDENT" | "TEACHER" | "PROFESSOR";

export interface UserProfileSettings {
  displayName: string;
  email: string;
  role: string;
  bio: string;
  learningGoal: string;
  characterAvatar: CharacterAvatarId;
  avatarColor: string;
  feynmanLevel: number;
  levelTitle: string;
}

export interface LearningSettings {
  rigorLevel: FeynmanRigorLevel;
  probingDepth: number; // 1 to 5
  defaultCharacter: CharacterAvatarId;
  evaluationStrictness: EvaluationStrictness;
  showReasoningSteps: boolean;
  autoGenerateReport: boolean;
  allowAnalogyTesting: boolean;
}

export interface AudioVoiceSettings {
  voicePersona: string;
  speechRate: number; // 0.8 to 1.5
  pitch: number;
  autoPlayAudio: boolean;
  soundEffects: boolean;
  micSensitivity: number; // 1 to 100
  noiseCancellation: boolean;
}

export interface PrivacyAndDataSettings {
  analyticsEnabled: boolean;
  autoSaveCloud: boolean;
  customGeminiApiKey: string;
  customElevenLabsApiKey: string;
}

export interface UserLearnerStats {
  conceptsMastered: number;
  gapsResolved: number;
  totalSessions: number;
  voiceMinutes: number;
  feynmanStreakDays: number;
}

export interface CurioSettingsState {
  theme: AppTheme;
  profile: UserProfileSettings;
  learning: LearningSettings;
  audio: AudioVoiceSettings;
  privacy: PrivacyAndDataSettings;
  stats: UserLearnerStats;
}
