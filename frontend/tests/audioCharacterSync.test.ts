import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { speechService } from "../services/speechService";
import {
  CharacterType,
  CharacterAnimationState,
  AudioLearningMode,
} from "../types/audioLearning";
import { CharacterId, PerformanceState } from "../types/performanceEngine";

// Headless harness that simulates useAudioCharacterSync logic and real lifecycle events
class AudioCharacterSyncController {
  public character: CharacterType;
  public characterId: CharacterId;
  public animationState: CharacterAnimationState;
  public performanceState: PerformanceState;
  public isPlayingSpeech: boolean = false;
  public isTeacherActive: boolean = false;
  public clipboardMark: "none" | "check" | "cross" | "in-progress" = "none";
  public currentSpeechText: string = "";
  public spokenCharIndex: number = 0;
  public activeSessionId: string | null = null;
  public activeTurnIndex: number = 0;
  public interventionStartCount: number = 0;
  public interventionEndCount: number = 0;
  public isMounted: boolean = true;

  constructor(initialMode: AudioLearningMode = "STUDENT") {
    this.character = initialMode === "PROFESSOR" ? "professor" : "student";
    this.characterId = initialMode === "PROFESSOR" ? "PROFESSOR" : "STUDENT";
    this.animationState = "idle";
    this.performanceState = "IDLE";
  }

  private updatePerformanceState(): void {
    const charId: CharacterId =
      this.character === "teacher" || this.isTeacherActive
        ? "TEACHER"
        : this.character === "professor"
        ? "PROFESSOR"
        : "STUDENT";
    this.characterId = charId;

    if (this.isPlayingSpeech) {
      this.performanceState = charId === "TEACHER" ? "EXPLAINING" : "SPEAKING";
      return;
    }

    switch (this.animationState) {
      case "recording":
      case "listening":
        this.performanceState = "LISTENING_ACTIVE";
        break;
      case "transcribing":
      case "thinking":
        this.performanceState = "THINKING";
        break;
      case "speaking":
        this.performanceState = charId === "TEACHER" ? "EXPLAINING" : "SPEAKING";
        break;
      case "explaining":
        this.performanceState = "EXPLAINING";
        break;
      case "asking":
      case "curious":
        this.performanceState = "ASKING";
        break;
      case "taking_notes":
        this.performanceState = "TAKING_NOTES";
        break;
      case "marking":
        this.performanceState = "MARKING";
        break;
      case "impressed":
        this.performanceState = "REACTING_POSITIVE";
        break;
      case "confused":
        this.performanceState = "REACTING_CONFUSED";
        break;
      case "skeptical":
      case "disappointed":
        this.performanceState = "REACTING_STRICT";
        break;
      case "grumpy":
        this.performanceState = "REACTING_GRUMPY";
        break;
      case "leaving":
        this.performanceState = "EXITING";
        break;
      case "teacher_transition":
        this.performanceState = "ENTERING";
        break;
      case "idle":
      default:
        this.performanceState = "IDLE";
        break;
    }
  }

  public setSessionId(id: string): void {
    if (!this.isMounted) return;
    this.activeSessionId = id;
    this.activeTurnIndex = 1;
  }

  public setMode(mode: AudioLearningMode): void {
    if (!this.isMounted) return;
    speechService.stop();
    if (mode === "PROFESSOR") {
      this.character = "professor";
      this.isTeacherActive = false;
    } else {
      this.character = "student";
      this.isTeacherActive = false;
    }
    this.animationState = "idle";
    this.clipboardMark = "none";
    this.updatePerformanceState();
  }

  public handleRecordingStart(): void {
    if (!this.isMounted) return;
    speechService.stop();
    this.animationState = "recording";
    this.updatePerformanceState();
  }

  public handleRecordingStop(): void {
    if (!this.isMounted) return;
    if (this.animationState === "recording") {
      this.animationState = "thinking";
      this.updatePerformanceState();
    }
  }

  public handleTranscriptionStart(): void {
    if (!this.isMounted) return;
    this.animationState = "transcribing";
    this.updatePerformanceState();
  }

  public handleAnswerSubmit(mode: AudioLearningMode): void {
    if (!this.isMounted) return;
    speechService.stop();
    if (mode === "PROFESSOR") {
      this.animationState = "marking";
      this.clipboardMark = "in-progress";
    } else {
      this.animationState = "taking_notes";
    }
    this.updatePerformanceState();
  }

  public handleEvaluationReceived(
    mode: AudioLearningMode,
    nextMode: string,
    shouldRestoreInterrupted: boolean,
    correctness: number = 0.7,
    incomingSessionId?: string
  ): boolean {
    if (!this.isMounted) return false;
    // Late asynchronous event protection: ignore if event belongs to older session
    if (incomingSessionId && incomingSessionId !== this.activeSessionId) {
      return false;
    }

    if (mode === "STUDENT") {
      if (nextMode === "TEACHER" && !this.isTeacherActive) {
        this.isTeacherActive = true;
        this.character = "teacher";
        this.animationState = "teacher_transition";
        this.interventionStartCount++;
        this.updatePerformanceState();
        return true;
      }

      if (shouldRestoreInterrupted && this.isTeacherActive) {
        this.isTeacherActive = false;
        this.character = "student";
        this.animationState = "impressed";
        this.interventionEndCount++;
        this.updatePerformanceState();
        return true;
      }

      if (correctness >= 0.8) {
        this.animationState = "impressed";
      } else if (correctness < 0.5) {
        this.animationState = "confused";
      } else {
        this.animationState = "curious";
      }
    } else {
      if (correctness >= 0.8) {
        this.animationState = "impressed";
        this.clipboardMark = "check";
      } else if (correctness < 0.4) {
        this.animationState = "skeptical";
        this.clipboardMark = "cross";
      } else {
        this.animationState = "idle";
        this.clipboardMark = "none";
      }
    }

    this.updatePerformanceState();
    return true;
  }

  public handleProfessorSkip(nextUnansweredCount: number): void {
    if (!this.isMounted) return;
    if (nextUnansweredCount >= 3) {
      this.animationState = "grumpy";
      this.clipboardMark = "cross";
    } else {
      this.animationState = "skeptical";
      this.clipboardMark = "cross";
    }
    this.updatePerformanceState();
  }

  public handleSpeechStart(cleanText: string): void {
    if (!this.isMounted) return;
    this.currentSpeechText = cleanText;
    this.spokenCharIndex = 0;
    this.isPlayingSpeech = true;
    this.animationState = "speaking";
    this.updatePerformanceState();
  }

  public handleSpeechBoundary(charIndex: number): void {
    if (!this.isMounted) return;
    this.spokenCharIndex = charIndex;
  }

  public handleSpeechEnd(): void {
    if (!this.isMounted) return;
    this.isPlayingSpeech = false;
    this.animationState = "idle";
    this.spokenCharIndex = 0;
    this.updatePerformanceState();
  }

  public handleSpeechInterrupt(): void {
    if (!this.isMounted) return;
    speechService.stop();
    this.isPlayingSpeech = false;
    this.animationState = "idle";
    this.spokenCharIndex = 0;
    this.updatePerformanceState();
  }

  public resetController(mode: AudioLearningMode = "STUDENT"): void {
    speechService.stop();
    this.activeSessionId = null;
    this.activeTurnIndex = 0;
    this.isPlayingSpeech = false;
    this.currentSpeechText = "";
    this.spokenCharIndex = 0;
    this.setMode(mode);
  }

  public unmount(): void {
    this.isMounted = false;
    speechService.stop();
  }
}

describe("Audio Character Synchronization Integration Suite", () => {
  let controller: AudioCharacterSyncController;

  beforeEach(() => {
    controller = new AudioCharacterSyncController("STUDENT");
  });

  afterEach(() => {
    controller.unmount();
  });

  describe("1. Identity & Default Stage Rendering", () => {
    test("Audio Mode initializes Student Leo as default character", () => {
      assert.strictEqual(controller.character, "student");
      assert.strictEqual(controller.characterId, "STUDENT");
      assert.strictEqual(controller.performanceState, "IDLE");
      assert.strictEqual(controller.animationState, "idle");
    });

    test("Professor Mode initializes Prof. Sterling", () => {
      const profController = new AudioCharacterSyncController("PROFESSOR");
      assert.strictEqual(profController.character, "professor");
      assert.strictEqual(profController.characterId, "PROFESSOR");
      assert.strictEqual(profController.performanceState, "IDLE");
      profController.unmount();
    });
  });

  describe("2. Microphone & Audio Lifecycle Mapping", () => {
    test("Microphone recording maps student to listening state", () => {
      controller.handleRecordingStart();
      assert.strictEqual(controller.animationState, "recording");
      assert.strictEqual(controller.performanceState, "LISTENING_ACTIVE");
    });

    test("Recording stop maps to thinking state before transcription", () => {
      controller.handleRecordingStart();
      controller.handleRecordingStop();
      assert.strictEqual(controller.animationState, "thinking");
      assert.strictEqual(controller.performanceState, "THINKING");
    });

    test("Transcription and AI submission map to note-taking for Student", () => {
      controller.handleTranscriptionStart();
      assert.strictEqual(controller.animationState, "transcribing");
      assert.strictEqual(controller.performanceState, "THINKING");

      controller.handleAnswerSubmit("STUDENT");
      assert.strictEqual(controller.animationState, "taking_notes");
      assert.strictEqual(controller.performanceState, "TAKING_NOTES");
    });

    test("AI submission maps to marking rubric on clipboard for Professor", () => {
      controller.setMode("PROFESSOR");
      controller.handleAnswerSubmit("PROFESSOR");
      assert.strictEqual(controller.animationState, "marking");
      assert.strictEqual(controller.performanceState, "MARKING");
      assert.strictEqual(controller.clipboardMark, "in-progress");
    });
  });

  describe("3. Speech Playback Lifecycle Synchronization", () => {
    test("Actual speech playback start sets speaking animation and captions", () => {
      const speechText = "Hi! I am Leo, let us explore photosynthesis.";
      controller.handleSpeechStart(speechText);
      assert.strictEqual(controller.isPlayingSpeech, true);
      assert.strictEqual(controller.currentSpeechText, speechText);
      assert.strictEqual(controller.animationState, "speaking");
      assert.strictEqual(controller.performanceState, "SPEAKING");
    });

    test("Speech boundary event tracks word position for live captions", () => {
      controller.handleSpeechStart("Learning quantum mechanics is rewarding.");
      controller.handleSpeechBoundary(16);
      assert.strictEqual(controller.spokenCharIndex, 16);
    });

    test("Speech playback completion returns character to neutral idle state", () => {
      controller.handleSpeechStart("Short explanation.");
      controller.handleSpeechEnd();
      assert.strictEqual(controller.isPlayingSpeech, false);
      assert.strictEqual(controller.animationState, "idle");
      assert.strictEqual(controller.performanceState, "IDLE");
      assert.strictEqual(controller.spokenCharIndex, 0);
    });

    test("Speech playback cancellation or error cleanly restores idle", () => {
      controller.handleSpeechStart("Unfinished dialogue interrupted by user.");
      controller.handleSpeechInterrupt();
      assert.strictEqual(controller.isPlayingSpeech, false);
      assert.strictEqual(controller.animationState, "idle");
      assert.strictEqual(controller.performanceState, "IDLE");
    });
  });

  describe("4. Teacher Mode & Automatic Interventions", () => {
    test("Concept gap triggers Teacher intervention and swaps visible character to Ms. Clara", () => {
      controller.setSessionId("sess_intervention_test");
      assert.strictEqual(controller.character, "student");

      const handled = controller.handleEvaluationReceived("STUDENT", "TEACHER", false, 0.3);
      assert.strictEqual(handled, true);
      assert.strictEqual(controller.isTeacherActive, true);
      assert.strictEqual(controller.character, "teacher");
      assert.strictEqual(controller.characterId, "TEACHER");
      assert.strictEqual(controller.animationState, "teacher_transition");
      assert.strictEqual(controller.performanceState, "ENTERING");
      assert.strictEqual(controller.interventionStartCount, 1);
    });

    test("Teacher speaks with EXPLAINING performance state", () => {
      controller.handleEvaluationReceived("STUDENT", "TEACHER", false, 0.3);
      controller.handleSpeechStart("Let me clarify how photons excite chlorophyll molecules.");
      assert.strictEqual(controller.characterId, "TEACHER");
      assert.strictEqual(controller.performanceState, "EXPLAINING");
    });

    test("Concept verified returns to Student Leo with impressed inquiry reaction", () => {
      controller.handleEvaluationReceived("STUDENT", "TEACHER", false, 0.3);
      assert.strictEqual(controller.isTeacherActive, true);

      // Restoration event after student clarifies the gap
      controller.handleEvaluationReceived("STUDENT", "STUDENT", true, 0.9);
      assert.strictEqual(controller.isTeacherActive, false);
      assert.strictEqual(controller.character, "student");
      assert.strictEqual(controller.characterId, "STUDENT");
      assert.strictEqual(controller.animationState, "impressed");
      assert.strictEqual(controller.performanceState, "REACTING_POSITIVE");
      assert.strictEqual(controller.interventionEndCount, 1);
    });
  });

  describe("5. Professor Mode Interview & Evaluation Rubric", () => {
    test("High correctness (>= 0.8) triggers impressed reaction and checkmark on clipboard", () => {
      controller.setMode("PROFESSOR");
      controller.handleEvaluationReceived("PROFESSOR", "PROFESSOR", false, 0.88);
      assert.strictEqual(controller.animationState, "impressed");
      assert.strictEqual(controller.performanceState, "REACTING_POSITIVE");
      assert.strictEqual(controller.clipboardMark, "check");
    });

    test("Low correctness (< 0.4) triggers skeptical reaction and crossmark on clipboard", () => {
      controller.setMode("PROFESSOR");
      controller.handleEvaluationReceived("PROFESSOR", "PROFESSOR", false, 0.32);
      assert.strictEqual(controller.animationState, "skeptical");
      assert.strictEqual(controller.performanceState, "REACTING_STRICT");
      assert.strictEqual(controller.clipboardMark, "cross");
    });

    test("Three consecutive skips trigger grumpy departure sequence", () => {
      controller.setMode("PROFESSOR");
      controller.handleProfessorSkip(1);
      assert.strictEqual(controller.animationState, "skeptical");
      assert.strictEqual(controller.clipboardMark, "cross");

      controller.handleProfessorSkip(2);
      assert.strictEqual(controller.animationState, "skeptical");

      controller.handleProfessorSkip(3);
      assert.strictEqual(controller.animationState, "grumpy");
      assert.strictEqual(controller.performanceState, "REACTING_GRUMPY");
      assert.strictEqual(controller.clipboardMark, "cross");
    });
  });

  describe("6. Session Lifecycle, Race Condition & Cleanup Protection", () => {
    test("Late async response from an old session is ignored and cannot overwrite current state", () => {
      controller.setSessionId("session_alpha");
      assert.strictEqual(controller.activeSessionId, "session_alpha");

      // User navigates / restarts to new session
      controller.setSessionId("session_beta");

      // Late response from session_alpha arrives
      const handled = controller.handleEvaluationReceived(
        "STUDENT",
        "TEACHER",
        false,
        0.2,
        "session_alpha"
      );
      assert.strictEqual(handled, false);
      assert.strictEqual(controller.isTeacherActive, false);
      assert.strictEqual(controller.character, "student");
    });

    test("Resetting controller restores neutral clean state", () => {
      controller.handleSpeechStart("Dialogue...");
      controller.resetController("STUDENT");
      assert.strictEqual(controller.activeSessionId, null);
      assert.strictEqual(controller.isPlayingSpeech, false);
      assert.strictEqual(controller.currentSpeechText, "");
      assert.strictEqual(controller.animationState, "idle");
      assert.strictEqual(controller.performanceState, "IDLE");
      assert.strictEqual(controller.character, "student");
    });

    test("Unmounted controller ignores subsequent events", () => {
      controller.unmount();
      controller.handleRecordingStart();
      assert.strictEqual(controller.animationState, "idle");
      controller.handleSpeechStart("Ghost speech");
      assert.strictEqual(controller.isPlayingSpeech, false);
    });
  });
});
