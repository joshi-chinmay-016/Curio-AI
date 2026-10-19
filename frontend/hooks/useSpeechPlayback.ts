"use client";

import { useState, useEffect, useCallback } from "react";
import { speechService } from "@/services/speechService";
import { SpeechPlaybackState } from "@/types/speech";

export function useSpeechPlayback(messageId: string, content: string) {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const isSupported = speechService.isSupported();

  useEffect(() => {
    const unsubscribe = speechService.subscribe((state: SpeechPlaybackState) => {
      setIsPlaying(state.isPlaying && state.activeMessageId === messageId);
    });

    return () => {
      unsubscribe();
      // Clean up speech if this specific message bubble unmounts while speaking
      if (speechService.getActiveMessageId() === messageId) {
        speechService.stop();
      }
    };
  }, [messageId]);

  const play = useCallback(() => {
    speechService.speak(messageId, content);
  }, [messageId, content]);

  const stop = useCallback(() => {
    speechService.stop();
  }, []);

  const toggle = useCallback(() => {
    if (isPlaying) {
      stop();
    } else {
      play();
    }
  }, [isPlaying, play, stop]);

  return {
    isPlaying,
    isSupported,
    play,
    stop,
    toggle,
  };
}
