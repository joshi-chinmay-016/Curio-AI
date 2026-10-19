"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { VoiceRecordingState, VoiceRecorderOptions, TranscriptionResult } from "@/types/voice";
import {
  transcribeAudio,
  isVoiceRecordingSupported,
  getSupportedAudioMimeType,
} from "@/services/voiceService";

export function useAudioRecorder(options: VoiceRecorderOptions = {}) {
  const { maxDurationSeconds = 300, onTranscriptionSuccess, onError } = options;

  const [state, setState] = useState<VoiceRecordingState>("idle");
  const [duration, setDuration] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const isCanceledRef = useRef<boolean>(false);

  // Stop and release all microphone media tracks
  const stopMediaTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {}
      });
      streamRef.current = null;
    }
  }, []);

  // Clear timer
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Ensure full cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimer();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stop();
        } catch {}
      }
      stopMediaTracks();
    };
  }, [clearTimer, stopMediaTracks]);

  const clearError = useCallback(() => {
    setError(null);
    if (state === "error") {
      setState("idle");
    }
  }, [state]);

  const startRecording = useCallback(async () => {
    // Guard against double clicks / concurrent starts
    if (state !== "idle" && state !== "error") {
      return;
    }

    clearError();
    isCanceledRef.current = false;
    audioChunksRef.current = [];
    setDuration(0);

    if (!isVoiceRecordingSupported()) {
      const msg = "Voice recording is not supported in this browser.";
      setError(msg);
      setState("error");
      onError?.(new Error(msg));
      return;
    }

    try {
      setState("requesting_permission");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = getSupportedAudioMimeType();
      const recorderOptions: MediaRecorderOptions = mimeType ? { mimeType } : {};
      const recorder = new MediaRecorder(stream, recorderOptions);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstart = () => {
        setState("recording");
        clearTimer();
        timerRef.current = setInterval(() => {
          setDuration((prev) => {
            const next = prev + 1;
            if (next >= maxDurationSeconds) {
              // Auto-stop at max limit
              stopRecording();
            }
            return next;
          });
        }, 1000);
      };

      recorder.start(250); // Slice into 250ms chunks for smooth recording
    } catch (err: any) {
      stopMediaTracks();
      let errorMsg = "Could not access microphone.";
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        errorMsg = "Microphone permission denied. Please allow microphone access in your browser settings.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        errorMsg = "No microphone found on your device.";
      } else if (err.message) {
        errorMsg = err.message;
      }

      setError(errorMsg);
      setState("error");
      onError?.(new Error(errorMsg));
    }
  }, [state, clearError, maxDurationSeconds, clearTimer, stopMediaTracks, onError]);

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      return;
    }

    clearTimer();

    return new Promise<void>((resolve) => {
      recorder.onstop = async () => {
        stopMediaTracks();

        if (isCanceledRef.current) {
          audioChunksRef.current = [];
          setState("idle");
          resolve();
          return;
        }

        const mimeType = recorder.mimeType || "audio/webm";
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        audioChunksRef.current = [];

        if (audioBlob.size === 0) {
          const emptyMsg = "No audio recorded. Please try speaking again.";
          setError(emptyMsg);
          setState("error");
          onError?.(new Error(emptyMsg));
          resolve();
          return;
        }

        try {
          setState("transcribing");
          // Determine filename extension based on recorded mime type
          let ext = ".webm";
          if (mimeType.includes("ogg")) ext = ".ogg";
          else if (mimeType.includes("wav")) ext = ".wav";
          else if (mimeType.includes("mp4")) ext = ".mp4";

          const result: TranscriptionResult = await transcribeAudio(audioBlob, `recording${ext}`);
          setState("idle");
          if (result.text) {
            onTranscriptionSuccess?.(result.text, result);
          }
        } catch (transcribeErr: any) {
          const msg = transcribeErr?.message || "Failed to transcribe audio.";
          setError(msg);
          setState("error");
          onError?.(transcribeErr);
        } finally {
          resolve();
        }
      };

      try {
        recorder.stop();
      } catch {
        stopMediaTracks();
        setState("idle");
        resolve();
      }
    });
  }, [clearTimer, stopMediaTracks, onTranscriptionSuccess, onError]);

  const cancelRecording = useCallback(() => {
    isCanceledRef.current = true;
    clearTimer();
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      try {
        recorder.stop();
      } catch {}
    }
    stopMediaTracks();
    audioChunksRef.current = [];
    setDuration(0);
    setState("idle");
  }, [clearTimer, stopMediaTracks]);

  return {
    state,
    duration,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
    clearError,
    isRecording: state === "recording",
    isTranscribing: state === "transcribing",
    isRequestingPermission: state === "requesting_permission",
  };
}
