"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  Square,
  X,
  Loader2,
  FastForward,
  AlertTriangle,
} from "lucide-react";
import {
  transcribeAudio,
  isVoiceRecordingSupported,
  getSupportedAudioMimeType,
} from "@/services/voiceService";
import { curioToast } from "@/components/curio/CurioToast";

interface AudioControlsProps {
  onSendAnswer: (text: string) => Promise<void>;
  onSkipQuestion?: () => void;
  isBusyProcessing?: boolean;
  isPlayingSpeech?: boolean;
  isProfessorMode?: boolean;
  disabled?: boolean;
  onRecordingStateChange?: (isRecording: boolean) => void;
  onTranscribingStateChange?: (isTranscribing: boolean) => void;
}

export function AudioControls({
  onSendAnswer,
  onSkipQuestion,
  isBusyProcessing = false,
  isPlayingSpeech = false,
  isProfessorMode = false,
  disabled = false,
  onRecordingStateChange,
  onTranscribingStateChange,
}: AudioControlsProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [isSupported, setIsSupported] = useState(true);
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    setIsSupported(isVoiceRecordingSupported());
    return () => {
      stopTracks();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const stopTracks = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  };

  const startRecording = async () => {
    if (disabled || isBusyProcessing || isTranscribing || isPlayingSpeech) return;
    setPermissionError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      const mimeType = getSupportedAudioMimeType();
      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);

      audioChunksRef.current = [];
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stopTracks();
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }

        const audioBlob = new Blob(audioChunksRef.current, {
          type: mimeType || "audio/webm",
        });

        if (audioBlob.size === 0) {
          setIsRecording(false);
          onRecordingStateChange?.(false);
          return;
        }

        // Automatic Speech Recognition & Auto-Submission (Audio-First)
        setIsTranscribing(true);
        onTranscribingStateChange?.(true);

        try {
          const res = await transcribeAudio(audioBlob);
          const recognizedText = (res.text || "").trim();

          if (recognizedText.length > 0) {
            // Automatically submit recognized text directly to the learning engine!
            await onSendAnswer(recognizedText);
          } else {
            curioToast.info("UNHEARD", "I couldn't hear you clearly. Please tap the mic to speak again.");
          }
        } catch (err: any) {
          console.error("Transcription error:", err);
          curioToast.error("TRANSCRIPTION FAILED", "Could not process audio. Please try speaking again.");
        } finally {
          setIsTranscribing(false);
          onTranscribingStateChange?.(false);
        }
      };

      mediaRecorder.start(250);
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      onRecordingStateChange?.(true);

      setRecordingSeconds(0);
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      console.error("Microphone access error:", err);
      setPermissionError("Microphone access was denied. Please allow microphone permission in your browser.");
      curioToast.error("MIC PERMISSION REQUIRED", "Please allow microphone access to speak.");
      stopTracks();
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      onRecordingStateChange?.(false);
    }
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      audioChunksRef.current = []; // Discard chunks
      mediaRecorderRef.current.onstop = () => {
        stopTracks();
      };
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      onRecordingStateChange?.(false);
      if (timerRef.current) clearInterval(timerRef.current);
      setRecordingSeconds(0);
      curioToast.info("DISCARDED", "Audio recording cancelled.");
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  if (!isSupported) {
    return (
      <div className="w-full max-w-md p-4 bg-amber-50 border border-amber-300 rounded-[8px] text-amber-900 text-xs font-mono text-center">
        Your browser does not support audio recording. Please use Google Chrome, Microsoft Edge, or Firefox.
      </div>
    );
  }

  const isLocked = disabled || isBusyProcessing || isTranscribing || isPlayingSpeech;

  return (
    <div className="w-full max-w-xl flex flex-col items-center gap-3 px-4 select-none">
      {/* Microphone Permission Warning */}
      {permissionError && (
        <div className="w-full p-3 bg-rose-50 border border-rose-300 rounded-[8px] text-rose-800 text-xs font-mono flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{permissionError}</span>
        </div>
      )}

      {/* Main Touch-To-Speak Pod */}
      <div className="w-full bg-white border-2 border-navy rounded-[16px] p-5 shadow-[4px_6px_0_0_#0F2B4A] flex flex-col items-center gap-4">
        {/* Central Giant Voice Action Button */}
        <div className="relative">
          {/* Subtle pulse rings when recording */}
          {isRecording && (
            <div className="absolute -inset-3 rounded-full border-2 border-rose-500/60 animate-ping pointer-events-none" />
          )}

          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLocked && !isRecording}
            className={`h-20 w-20 rounded-full flex items-center justify-center transition-all cursor-pointer shadow-[0_4px_0_0_#0F2B4A] active:translate-y-[2px] active:shadow-none ${
              isRecording
                ? "bg-rose-600 text-white animate-pulse shadow-[0_0_24px_rgba(225,29,72,0.6)] border-3 border-rose-700"
                : isTranscribing
                ? "bg-amber-100 text-amber-700 border-3 border-amber-400"
                : isPlayingSpeech
                ? "bg-emerald-50 text-emerald-700 border-3 border-emerald-400 opacity-60 cursor-not-allowed"
                : isBusyProcessing
                ? "bg-cobalt/10 text-cobalt border-3 border-cobalt/30 opacity-60 cursor-not-allowed"
                : "bg-white text-navy hover:text-cobalt hover:border-cobalt border-3 border-navy hover:bg-ice/50"
            }`}
            title={
              isRecording
                ? "Tap to finish speaking (submits automatically)"
                : isPlayingSpeech
                ? "Listening to response..."
                : isBusyProcessing
                ? "Evaluating answer..."
                : "Tap to speak your answer"
            }
            aria-label={isRecording ? "Finish speaking" : "Start speaking"}
          >
            {isTranscribing ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : isRecording ? (
              <Square className="w-8 h-8 fill-current" />
            ) : (
              <Mic className="w-9 h-9" />
            )}
          </button>
        </div>

        {/* Audio State Label */}
        <div className="text-center">
          {isRecording ? (
            <div className="flex flex-col items-center gap-1">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-ping" />
                <span className="font-mono text-sm font-bold text-rose-600 tracking-wider">
                  LISTENING... {formatTime(recordingSeconds)}
                </span>
              </div>
              <span className="font-mono text-[11px] text-navy/60">
                Tap button when finished speaking
              </span>
            </div>
          ) : isTranscribing ? (
            <div className="flex items-center gap-2 text-amber-800">
              <span className="font-mono text-xs font-bold uppercase tracking-wider">
                Recognizing speech & submitting...
              </span>
            </div>
          ) : isPlayingSpeech ? (
            <div className="flex items-center gap-2 text-emerald-700 font-mono text-xs font-bold uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Listen to the response...
            </div>
          ) : isBusyProcessing ? (
            <div className="flex items-center gap-2 text-navy/60 font-mono text-xs font-bold uppercase tracking-wider">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-cobalt" />
              Evaluating answer...
            </div>
          ) : (
            <div className="flex flex-col items-center gap-0.5">
              <span className="font-heading text-sm font-bold text-navy">
                Tap to speak
              </span>
              <span className="font-mono text-[11px] text-navy/50">
                Audio is automatically submitted when you finish
              </span>
            </div>
          )}
        </div>

        {/* Live Audio Visualizer Equalizer during active speech */}
        {isRecording && (
          <div className="w-full flex items-center justify-center gap-1.5 py-2.5 bg-ice/70 border border-fog rounded-[8px]">
            <span className="w-1.5 h-4 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.4s]" />
            <span className="w-1.5 h-7 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.2s]" />
            <span className="w-1.5 h-3 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.5s]" />
            <span className="w-1.5 h-8 bg-rose-500 rounded-full animate-bounce" />
            <span className="w-1.5 h-5 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-1.5 h-7 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.1s]" />
            <span className="w-1.5 h-3 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.45s]" />
            <span className="font-mono text-[11px] uppercase text-rose-700 font-bold ml-2">
              Recording live speech
            </span>
          </div>
        )}

        {/* Bottom Helper Controls (Cancel Recording or Skip Question) */}
        <div className="flex items-center justify-between w-full pt-1">
          {isRecording ? (
            <button
              onClick={cancelRecording}
              className="px-3 py-1.5 rounded-[4px] border border-fog text-xs font-mono font-bold text-navy/60 hover:text-rose-600 hover:bg-rose-50 transition-colors inline-flex items-center gap-1.5 cursor-pointer mx-auto"
              title="Discard audio recording"
            >
              <X className="w-3.5 h-3.5" />
              CANCEL RECORDING
            </button>
          ) : isProfessorMode && onSkipQuestion && !isLocked ? (
            <button
              onClick={onSkipQuestion}
              className="px-3.5 py-1.5 rounded-[6px] border border-fog text-xs font-mono font-bold text-navy/70 hover:text-navy hover:bg-ice transition-colors inline-flex items-center gap-1.5 cursor-pointer mx-auto shadow-xs"
              title="Skip this question (counts as unanswered)"
            >
              <FastForward className="w-3.5 h-3.5 text-gap-orange" />
              SKIP QUESTION (PROFESSOR MODE)
            </button>
          ) : (
            <div className="h-6" />
          )}
        </div>
      </div>
    </div>
  );
}
