import { SpeechOptions, SpeechPlaybackState, SpeechProvider } from "@/types/speech";

/**
 * Sanitizes markdown content, code blocks, and formatting into clean,
 * natural text suitable for text-to-speech pronunciation.
 * Avoids reading raw syntax, internal tags, or code verbatim.
 */
export function sanitizeTextForSpeech(markdown: string): string {
  if (!markdown) return "";

  let text = markdown;

  // 1. Remove fenced code blocks (e.g. ```python ... ```)
  text = text.replace(/```[\s\S]*?```/g, " [Code block omitted] ");

  // 2. Remove inline code formatting `code`
  text = text.replace(/`([^`]+)`/g, "$1");

  // 3. Remove horizontal rules and ornamental line breaks
  text = text.replace(/^[─\-=*_]{3,}$/gm, " ");
  text = text.replace(/──[^─]+──/g, " ");

  // 4. Remove Markdown images ![alt](url)
  text = text.replace(/!\[([^\]]*)\]\([^)]*\)/g, " ");

  // 5. Replace Markdown links [title](url) with just title
  text = text.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1");

  // 6. Remove headings syntax (# Heading)
  text = text.replace(/^#{1,6}\s+/gm, "");

  // 7. Remove blockquote markers (> Quote)
  text = text.replace(/^>\s+/gm, "");

  // 8. Remove bullet lists and numbered list markers
  text = text.replace(/^\s*[-*+]\s+/gm, "");
  text = text.replace(/^\s*\d+\.\s+/gm, "");

  // 9. Remove bold and italics (*text*, **text**, _text_, __text__)
  text = text.replace(/(\*\*|__)(.*?)\1/g, "$2");
  text = text.replace(/(\*|_)(.*?)\1/g, "$2");

  // 10. Remove citation brackets like [1], [2]
  text = text.replace(/\[\d+\]/g, "");

  // 11. Collapse multiple whitespaces and trim
  text = text.replace(/\s+/g, " ").trim();

  return text;
}

/**
 * Browser implementation of SpeechProvider using the Web Speech API (speechSynthesis).
 * Modularized so alternative providers (e.g., self-hosted Piper TTS) can be swapped in.
 */
export class BrowserSpeechService implements SpeechProvider {
  private activeMessageId: string | null = null;
  private isCurrentlyPlaying: boolean = false;
  private isCurrentlyPaused: boolean = false;
  private listeners: Set<(state: SpeechPlaybackState) => void> = new Set();
  private voices: SpeechSynthesisVoice[] = [];
  private currentUtterance: any = null;

  constructor() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this.initVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => this.initVoices();
      }
    }
  }

  private initVoices() {
    try {
      this.voices = window.speechSynthesis.getVoices();
    } catch {
      this.voices = [];
    }
  }

  public isSupported(): boolean {
    return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  }

  public getActiveMessageId(): string | null {
    return this.activeMessageId;
  }

  public isPlaying(messageId?: string): boolean {
    if (messageId) {
      return this.isCurrentlyPlaying && this.activeMessageId === messageId;
    }
    return this.isCurrentlyPlaying;
  }

  public subscribe(listener: (state: SpeechPlaybackState) => void): () => void {
    this.listeners.add(listener);
    // Initial emit
    listener({
      activeMessageId: this.activeMessageId,
      isPlaying: this.isCurrentlyPlaying,
      isPaused: this.isCurrentlyPaused,
    });

    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify() {
    const state: SpeechPlaybackState = {
      activeMessageId: this.activeMessageId,
      isPlaying: this.isCurrentlyPlaying,
      isPaused: this.isCurrentlyPaused,
    };
    this.listeners.forEach((l) => {
      try {
        l(state);
      } catch {}
    });
  }

  private selectVoice(): SpeechSynthesisVoice | null {
    if (!this.voices || this.voices.length === 0) {
      this.initVoices();
    }
    if (!this.voices || this.voices.length === 0) return null;

    // Prefer high quality English voices (Google US English, Samantha, Microsoft Natural, etc.)
    const preferredNames = ["natural", "google", "samantha", "daniel", "karen", "moira", "jenny"];
    const englishVoices = this.voices.filter((v) => v.lang.startsWith("en"));

    for (const pref of preferredNames) {
      const match = englishVoices.find((v) => v.name.toLowerCase().includes(pref));
      if (match) return match;
    }

    return englishVoices[0] || this.voices[0] || null;
  }

  public async speak(messageId: string, text: string, options: SpeechOptions = {}): Promise<void> {
    if (!this.isSupported()) {
      const err = new Error("Browser text-to-speech is not supported.");
      options.onError?.(err);
      return;
    }

    const cleanText = sanitizeTextForSpeech(text);
    if (!cleanText) {
      // Empty or code-only response: nothing to speak
      return;
    }

    // If already speaking any message, cancel it first
    this.stop();

    const UtteranceClass =
      (typeof window !== "undefined" && (window as any).SpeechSynthesisUtterance) ||
      (typeof SpeechSynthesisUtterance !== "undefined" ? SpeechSynthesisUtterance : null);
    if (!UtteranceClass) {
      options.onError?.(new Error("SpeechSynthesisUtterance not supported."));
      return;
    }

    const utterance = new UtteranceClass(cleanText);
    utterance.rate = options.rate ?? 1.0;
    utterance.pitch = options.pitch ?? 1.0;
    utterance.volume = options.volume ?? 1.0;

    const voice = this.selectVoice();
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = "en-US";
    }

    utterance.onstart = () => {
      this.activeMessageId = messageId;
      this.isCurrentlyPlaying = true;
      this.isCurrentlyPaused = false;
      this.notify();
      options.onStart?.();
    };

    utterance.onend = () => {
      this.activeMessageId = null;
      this.isCurrentlyPlaying = false;
      this.isCurrentlyPaused = false;
      this.notify();
      options.onEnd?.();
    };

    utterance.onboundary = (event: any) => {
      if (event.name === "word" || event.charIndex !== undefined) {
        options.onBoundary?.(event.charIndex, event.charLength || 0);
      }
    };

    utterance.onerror = (event: SpeechSynthesisErrorEvent) => {
      // Ignore "canceled" or "interrupted" event caused by intentional user stop
      if (event.error === "canceled" || event.error === "interrupted") {
        this.activeMessageId = null;
        this.isCurrentlyPlaying = false;
        this.isCurrentlyPaused = false;
        this.notify();
        return;
      }

      this.activeMessageId = null;
      this.isCurrentlyPlaying = false;
      this.isCurrentlyPaused = false;
      this.notify();
      const err = new Error(`Speech synthesis error: ${event.error}`);
      options.onError?.(err);
    };

    this.currentUtterance = utterance;

    // Ensure speechSynthesis is active and not paused by browser
    if (typeof window !== "undefined" && window.speechSynthesis) {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    }

    // A 60ms delay ensures previous cancel() fully releases in Chromium engines
    setTimeout(() => {
      try {
        if (typeof window !== "undefined" && window.speechSynthesis) {
          window.speechSynthesis.resume();
          window.speechSynthesis.speak(utterance);
        }
      } catch (err) {
        console.error("Speech speak failed:", err);
        options.onError?.(err as Error);
      }
    }, 60);
  }

  public stop(): void {
    if (!this.isSupported()) return;

    try {
      window.speechSynthesis.cancel();
    } catch {}

    this.activeMessageId = null;
    this.isCurrentlyPlaying = false;
    this.isCurrentlyPaused = false;
    this.notify();
  }

  public pause(): void {
    if (!this.isSupported()) return;
    try {
      window.speechSynthesis.pause();
      this.isCurrentlyPaused = true;
      this.notify();
    } catch {}
  }

  public resume(): void {
    if (!this.isSupported()) return;
    try {
      window.speechSynthesis.resume();
      this.isCurrentlyPaused = false;
      this.notify();
    } catch {}
  }
}

// Global singleton instance for the browser session
export const speechService: SpeechProvider = new BrowserSpeechService();
