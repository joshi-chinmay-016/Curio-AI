export interface SpeechOptions {
  voice?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: Error) => void;
}

export interface SpeechPlaybackState {
  activeMessageId: string | null;
  isPlaying: boolean;
  isPaused: boolean;
}

export interface SpeechProvider {
  speak(messageId: string, text: string, options?: SpeechOptions): Promise<void>;
  stop(): void;
  pause(): void;
  resume(): void;
  isPlaying(messageId?: string): boolean;
  isSupported(): boolean;
  getActiveMessageId(): string | null;
  subscribe(listener: (state: SpeechPlaybackState) => void): () => void;
}
