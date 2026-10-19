import { apiClient } from "@/services/apiClient";
import { TranscriptionResult } from "@/types/voice";

/**
 * Sends recorded audio Blob to Curio AI's authenticated transcription endpoint.
 * Reuses the existing apiClient, maintaining bearer tokens and multipart form handling.
 */
export async function transcribeAudio(
  audioBlob: Blob,
  filename: string = "recording.webm"
): Promise<TranscriptionResult> {
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error("Recording is empty (0 bytes). Please try speaking again.");
  }

  const formData = new FormData();
  formData.append("file", audioBlob, filename);

  // apiClient automatically attaches Authorization header and delegates boundary creation to the browser
  return await apiClient<TranscriptionResult>("/voice/transcribe", {
    method: "POST",
    body: formData,
  });
}

/**
 * Checks if the browser supports media recording with microphone.
 */
export function isVoiceRecordingSupported(): boolean {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return false;
  }
  return Boolean(
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function" &&
    typeof (window as any).MediaRecorder === "function"
  );
}

/**
 * Select the optimal supported MIME format for audio recording.
 */
export function getSupportedAudioMimeType(): string {
  if (typeof window === "undefined" || typeof (window as any).MediaRecorder === "undefined") {
    return "audio/webm";
  }

  const MediaRecorderClass = (window as any).MediaRecorder;
  if (typeof MediaRecorderClass.isTypeSupported !== "function") {
    return "audio/webm";
  }

  const candidateTypes = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
    "audio/wav",
  ];

  for (const type of candidateTypes) {
    if (MediaRecorderClass.isTypeSupported(type)) {
      return type;
    }
  }

  return "";
}
