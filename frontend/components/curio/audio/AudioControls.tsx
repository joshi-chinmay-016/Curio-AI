"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic,
  Square,
  X,
  Loader2,
  FastForward,
  AlertTriangle,
  Volume2,
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

  // VAD / Automatic Silence Detection State
  const [speechDetected, setSpeechDetected] = useState(false);
  const [silenceCountdown, setSilenceCountdown] = useState<number | null>(null);
  const [volumeLevel, setVolumeLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const vadIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const recognitionRef = useRef<any>(null);
  const liveTranscriptRef = useRef<string>("");
  const hasSpokenRef = useRef<boolean>(false);
  const silenceStartRef = useRef<number | null>(null);

  useEffect(() => {
    setIsSupported(isVoiceRecordingSupported());
    return () => {
      cleanupResources();
    };
  }, []);

  const cleanupResources = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    onRecordingStateChange?.(false);
    setSpeechDetected(false);
    setSilenceCountdown(null);
  }, [onRecordingStateChange]);

  const startRecording = async () => {
    if (disabled || isBusyProcessing || isTranscribing || isPlayingSpeech) return;
    setPermissionError(null);
    hasSpokenRef.current = false;
    silenceStartRef.current = null;
    liveTranscriptRef.current = "";
    setSpeechDetected(false);
    setSilenceCountdown(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // 1. Initialize Web Audio API Analyser for Voice Activity & Silence Detection
      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          const audioCtx = new AudioCtx();
          audioContextRef.current = audioCtx;
          const sourceNode = audioCtx.createMediaStreamSource(stream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 256;
          sourceNode.connect(analyser);

          const bufferLength = analyser.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);

          const SILENCE_TIMEOUT_MS = 1800; // 1.8 seconds of silence after speech triggers auto-send
          const SPEECH_VOLUME_THRESHOLD = 12; // Volume threshold for human speech

          vadIntervalRef.current = setInterval(() => {
            if (!analyser) return;
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
              sum += dataArray[i];
            }
            const avg = sum / bufferLength;
            setVolumeLevel(Math.min(100, Math.round(avg * 2.5)));

            if (avg >= SPEECH_VOLUME_THRESHOLD) {
              // Active speech detected!
              hasSpokenRef.current = true;
              silenceStartRef.current = null;
              setSpeechDetected(true);
              setSilenceCountdown(null);
            } else if (hasSpokenRef.current) {
              // User has spoken at least once and is currently pausing
              const now = Date.now();
              if (!silenceStartRef.current) {
                silenceStartRef.current = now;
              }
              const elapsed = now - silenceStartRef.current;
              const remainingSec = Math.max(0, (SILENCE_TIMEOUT_MS - elapsed) / 1000);
              setSilenceCountdown(parseFloat(remainingSec.toFixed(1)));

              if (elapsed >= SILENCE_TIMEOUT_MS) {
                // Auto-endpoint reached: Automatically finish and submit!
                console.log("[Curio Audio] Silence detected after speech. Automatically sending answer!");
                if (vadIntervalRef.current) {
                  clearInterval(vadIntervalRef.current);
                  vadIntervalRef.current = null;
                }
                stopRecording();
              }
            }
          }, 80);
        }
      } catch (audioErr) {
        console.warn("Web Audio Analyser not available:", audioErr);
      }

      // 2. Parallel Browser Speech Recognition for instant zero-delay transcript
      const SpeechRecognitionClass =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognitionClass) {
        try {
          const recognition = new SpeechRecognitionClass();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = "en-US";

          recognition.onresult = (event: any) => {
            let fullText = "";
            for (let i = 0; i < event.results.length; ++i) {
              fullText += event.results[i][0].transcript + " ";
            }
            if (fullText.trim()) {
              liveTranscriptRef.current = fullText.trim();
              hasSpokenRef.current = true;
              setSpeechDetected(true);
            }
          };

          recognition.onerror = () => {};
          recognition.start();
          recognitionRef.current = recognition;
        } catch {}
      }

      // 3. MediaRecorder for high-fidelity audio capture to Whisper
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
        cleanupResources();

        const audioBlob = new Blob(audioChunksRef.current, {
          type: mimeType || "audio/webm",
        });

        // Begin Automatic Transcription & Submission
        setIsTranscribing(true);
        onTranscribingStateChange?.(true);

        try {
          let recognizedText = "";

          // First try Whisper backend
          if (audioBlob.size > 0) {
            try {
              const res = await transcribeAudio(audioBlob);
              recognizedText = (res.text || "").trim();
            } catch (whisperErr) {
              console.warn("Whisper transcription fallback to browser recognition:", whisperErr);
            }
          }

          // If Whisper was empty or errored, use browser Web Speech transcript
          if (!recognizedText && liveTranscriptRef.current) {
            recognizedText = liveTranscriptRef.current.trim();
          }

          if (recognizedText.length > 0) {
            // AUTOMATICALLY SUBMIT SPEECH (No confirm dialog, no text input)
            await onSendAnswer(recognizedText);
          } else {
            curioToast.info("UNHEARD", "I couldn't hear you clearly. Please tap to speak again.");
          }
        } catch (err: any) {
          console.error("Transcription & Submission error:", err);
          curioToast.error("SUBMISSION FAILED", "Could not submit speech. Please try again.");
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
      cleanupResources();
    }
  };

  const cancelRecording = () => {
    audioChunksRef.current = [];
    liveTranscriptRef.current = "";
    cleanupResources();
    setIsRecording(false);
    onRecordingStateChange?.(false);
    setSpeechDetected(false);
    setSilenceCountdown(null);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  if (!isSupported) {
    return (
      <div className="w-full max-w-xl p-4 bg-amber-50 border border-amber-300 rounded-[12px] text-amber-900 text-sm font-mono text-center">
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
            <div
              className={`absolute -inset-3 rounded-full border-2 transition-all pointer-events-none ${
                speechDetected
                  ? "border-emerald-500/80 animate-ping"
                  : "border-rose-500/60 animate-pulse"
              }`}
            />
          )}

          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLocked && !isRecording}
            className={`h-20 w-20 rounded-full flex items-center justify-center transition-all cursor-pointer shadow-[0_4px_0_0_#0F2B4A] active:translate-y-[2px] active:shadow-none ${
              isRecording
                ? speechDetected
                  ? "bg-emerald-600 text-white shadow-[0_0_30px_rgba(16,185,129,0.7)] border-3 border-emerald-700 animate-pulse"
                  : "bg-rose-600 text-white shadow-[0_0_24px_rgba(225,29,72,0.6)] border-3 border-rose-700"
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
                ? "Tap to finish speaking (or simply pause to auto-submit)"
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

        {/* Dynamic Voice State & Auto-Sending Label */}
        <div className="text-center">
          {isRecording ? (
            <div className="flex flex-col items-center gap-1.5">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    speechDetected
                      ? "bg-emerald-500 animate-ping"
                      : "bg-rose-600 animate-pulse"
                  }`}
                />
                <span className="font-mono text-sm font-bold text-navy tracking-wider">
                  {speechDetected ? "SPEECH DETECTED" : "LISTENING..."} ({formatTime(recordingSeconds)})
                </span>
              </div>

              {/* Automatic Silence Countdown indicator */}
              {silenceCountdown !== null && silenceCountdown > 0 ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 border border-amber-300 rounded-full text-amber-900 font-mono text-xs font-semibold animate-pulse">
                  <span>Auto-sending in {silenceCountdown}s...</span>
                </div>
              ) : (
                <span className="font-mono text-[11px] text-navy/60">
                  Speak naturally — auto-submits when you pause
                </span>
              )}
            </div>
          ) : isTranscribing ? (
            <div className="flex items-center gap-2 text-amber-800">
              <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
              <span className="font-mono text-xs font-bold uppercase tracking-wider">
                Recognizing speech & submitting automatically...
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
                Speaks naturally — automatically submits when you stop
              </span>
            </div>
          )}
        </div>

        {/* Live Audio Volume Visualizer during active speech */}
        {isRecording && (
          <div className="w-full flex items-center justify-center gap-1.5 py-2.5 bg-ice/70 border border-fog rounded-[8px]">
            <span
              className="w-1.5 bg-emerald-500 rounded-full transition-all duration-75"
              style={{ height: `${Math.max(6, volumeLevel * 0.4)}px` }}
            />
            <span
              className="w-1.5 bg-emerald-500 rounded-full transition-all duration-75"
              style={{ height: `${Math.max(8, volumeLevel * 0.7)}px` }}
            />
            <span
              className="w-1.5 bg-emerald-500 rounded-full transition-all duration-75"
              style={{ height: `${Math.max(6, volumeLevel * 0.5)}px` }}
            />
            <span
              className="w-1.5 bg-emerald-500 rounded-full transition-all duration-75"
              style={{ height: `${Math.max(10, volumeLevel * 0.9)}px` }}
            />
            <span
              className="w-1.5 bg-emerald-500 rounded-full transition-all duration-75"
              style={{ height: `${Math.max(8, volumeLevel * 0.6)}px` }}
            />
            <span
              className="w-1.5 bg-emerald-500 rounded-full transition-all duration-75"
              style={{ height: `${Math.max(6, volumeLevel * 0.4)}px` }}
            />
            <span className="font-mono text-[11px] uppercase text-navy font-bold ml-2">
              {speechDetected ? "Capturing voice" : "Waiting for voice"}
            </span>
          </div>
        )}

        {/* Bottom Helper Controls (Cancel Recording or Skip Question) */}
        <div className="flex items-center justify-between w-full pt-1">
          {isRecording ? (
            <button
              type="button"
              onClick={cancelRecording}
              className="inline-flex items-center gap-1 text-xs font-mono font-bold text-navy/50 hover:text-rose-600 transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              Cancel recording
            </button>
          ) : (
            <div className="text-[11px] font-mono text-navy/40">
              Audio-only mode · No typing needed
            </div>
          )}

          {isProfessorMode && onSkipQuestion && !isRecording && (
            <button
              type="button"
              onClick={onSkipQuestion}
              disabled={isLocked}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-ice hover:bg-fog/30 text-navy/70 hover:text-navy text-xs font-mono font-bold rounded-[6px] border border-fog transition-colors disabled:opacity-40 cursor-pointer"
              title="Skip this question (counts as unanswered strike)"
            >
              <FastForward className="w-3 h-3 text-gap-orange" />
              Skip question
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
