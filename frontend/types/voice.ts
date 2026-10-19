export interface TranscriptionResult {
  text: string;
  language: string;
  duration_seconds?: number | null;
}

export type VoiceRecordingState =
  | "idle"
  | "requesting_permission"
  | "recording"
  | "transcribing"
  | "error";

export interface VoiceRecorderOptions {
  maxDurationSeconds?: number;
  onTranscriptionSuccess?: (text: string, result: TranscriptionResult) => void;
  onError?: (error: Error) => void;
}
