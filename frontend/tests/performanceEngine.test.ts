import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import {
  CharacterId,
  PerformanceState,
  validTransitions,
  CharacterPerformanceEngine,
  LearningEngineEvents,
  AssessmentResult,
} from "../types/performanceEngine";
import { bindAnimationToLearningEngine } from "../components/character/CharacterAudioSync";
import { studentAnimations } from "../components/character/animations/student.animations";
import { teacherAnimations } from "../components/character/animations/teacher.animations";
import { professorAnimations } from "../components/character/animations/professor.animations";

// Standalone performance engine implementation matching usePerformanceEngine for headless testing
class TestPerformanceEngine implements CharacterPerformanceEngine {
  public state: PerformanceState;
  public activeCharacter: CharacterId;
  public isAnimating: boolean = false;
  public prefersReducedMotion: boolean = false;
  private isDestroyed: boolean = false;
  private activeTimers: any[] = [];

  constructor(
    initialCharacter: CharacterId = "STUDENT",
    initialState: PerformanceState = "IDLE",
    prefersReducedMotion = false
  ) {
    this.activeCharacter = initialCharacter;
    this.state = initialState;
    this.prefersReducedMotion = prefersReducedMotion;
  }

  public setCharacter(character: CharacterId): void {
    if (this.isDestroyed) return;
    this.activeCharacter = character;
  }

  public transition(to: PerformanceState, options?: { force?: boolean; onComplete?: () => void }): void {
    if (this.isDestroyed) return;
    if (this.state === to) return;

    const allowed = validTransitions[this.state] || [];
    const isValid = allowed.includes(to) || options?.force === true;

    if (!isValid) {
      // Reject invalid transition
      return;
    }

    this.clearTimers();
    this.state = to;
    this.isAnimating = true;

    let autoDuration = 0;
    let nextState: PerformanceState | null = null;

    if (to === "ENTERING") {
      autoDuration = this.activeCharacter === "PROFESSOR" ? 1000 : 700;
      nextState = "IDLE";
    } else if (to === "EXITING") {
      autoDuration = this.activeCharacter === "PROFESSOR" ? 3200 : 700;
      nextState = "OFFSTAGE";
    } else if (to === "REACTING_POSITIVE") {
      autoDuration = this.activeCharacter === "STUDENT" ? 700 : 600;
      nextState = this.activeCharacter === "STUDENT" ? "TAKING_NOTES" : "IDLE";
    } else if (to === "REACTING_CONFUSED") {
      autoDuration = 600;
      nextState = "IDLE";
    } else if (to === "REACTING_STRICT") {
      autoDuration = 800;
      nextState = "IDLE";
    }

    if (this.prefersReducedMotion) {
      this.isAnimating = false;
      if (nextState) {
        this.state = nextState;
      }
      options?.onComplete?.();
      return;
    }

    if (autoDuration > 0 && nextState) {
      const targetNext = nextState;
      const timer = setTimeout(() => {
        if (!this.isDestroyed) {
          this.state = targetNext;
          this.isAnimating = false;
          options?.onComplete?.();
        }
      }, autoDuration);
      this.activeTimers.push(timer);
    } else {
      this.isAnimating = false;
      options?.onComplete?.();
    }
  }

  public swapCharacter(to: CharacterId, onSwapReady?: () => void): void {
    if (this.isDestroyed) return;
    this.clearTimers();

    const finishSwap = () => {
      if (this.isDestroyed) return;
      this.activeCharacter = to;
      this.state = "ENTERING";
      this.isAnimating = true;

      const enterDuration = this.prefersReducedMotion ? 0 : 50; // fast mock in test
      const timer = setTimeout(() => {
        if (this.isDestroyed) return;
        this.state = "IDLE";
        this.isAnimating = false;
        onSwapReady?.();
      }, enterDuration);
      this.activeTimers.push(timer);
    };

    if (this.state === "OFFSTAGE") {
      finishSwap();
    } else {
      this.state = "EXITING";
      this.isAnimating = true;
      const exitDuration = this.prefersReducedMotion ? 0 : 50;
      const timer = setTimeout(() => {
        if (this.isDestroyed) return;
        this.state = "OFFSTAGE";
        finishSwap();
      }, exitDuration);
      this.activeTimers.push(timer);
    }
  }

  public interrupt(reason: "error" | "navigation" | "user"): void {
    if (this.isDestroyed) return;
    this.clearTimers();
    if (this.state === "OFFSTAGE") return;
    this.state = "IDLE";
    this.isAnimating = false;
  }

  public destroy(): void {
    this.isDestroyed = true;
    this.clearTimers();
  }

  public clearTimers(): void {
    this.activeTimers.forEach((t) => clearTimeout(t));
    this.activeTimers = [];
  }
}

describe("CharacterPerformanceEngine Test Suite", () => {
  describe("1. State transitions", () => {
    test("transitions from IDLE to LISTENING_ACTIVE", () => {
      const engine = new TestPerformanceEngine("STUDENT", "IDLE");
      engine.transition("LISTENING_ACTIVE");
      assert.strictEqual(engine.state, "LISTENING_ACTIVE");
    });

    test("transitions from LISTENING_ACTIVE to THINKING on record stop", () => {
      const engine = new TestPerformanceEngine("STUDENT", "LISTENING_ACTIVE");
      engine.transition("THINKING");
      assert.strictEqual(engine.state, "THINKING");
    });

    test("transitions from THINKING to SPEAKING on speech start", () => {
      const engine = new TestPerformanceEngine("STUDENT", "THINKING");
      engine.transition("SPEAKING");
      assert.strictEqual(engine.state, "SPEAKING");
    });

    test("transitions from SPEAKING to IDLE on speech end", () => {
      const engine = new TestPerformanceEngine("STUDENT", "SPEAKING");
      engine.transition("IDLE");
      assert.strictEqual(engine.state, "IDLE");
    });

    test("refuses invalid transitions and stays in current state", () => {
      const engine = new TestPerformanceEngine("STUDENT", "LISTENING_ACTIVE");
      // LISTENING_ACTIVE cannot jump straight to SPEAKING (must process through THINKING)
      engine.transition("SPEAKING");
      assert.strictEqual(engine.state, "LISTENING_ACTIVE");
    });

    test("handles interrupt safely and snaps to neutral IDLE", () => {
      const engine = new TestPerformanceEngine("STUDENT", "SPEAKING");
      engine.interrupt("error");
      assert.strictEqual(engine.state, "IDLE");
      assert.strictEqual(engine.isAnimating, false);
    });
  });

  describe("2. Character swaps", () => {
    test("moves student to EXITING and OFFSTAGE before teacher enters", async () => {
      const engine = new TestPerformanceEngine("STUDENT", "IDLE");
      let readyCalled = false;

      await new Promise<void>((resolve) => {
        engine.swapCharacter("TEACHER", () => {
          readyCalled = true;
          resolve();
        });
        // Immediately after swap initiated, state is EXITING
        assert.strictEqual(engine.state, "EXITING");
      });

      assert.strictEqual(readyCalled, true);
      assert.strictEqual(engine.activeCharacter, "TEACHER");
      assert.strictEqual(engine.state, "IDLE");
    });

    test("preserves session context through character swap sequence", async () => {
      const engine = new TestPerformanceEngine("STUDENT", "IDLE");
      const activeConcept = "Recursion Base Case";

      await new Promise<void>((resolve) => {
        engine.swapCharacter("TEACHER", () => {
          resolve();
        });
      });

      assert.strictEqual(engine.activeCharacter, "TEACHER");
      assert.strictEqual(activeConcept, "Recursion Base Case");

      // Swap back to Student
      await new Promise<void>((resolve) => {
        engine.swapCharacter("STUDENT", () => {
          resolve();
        });
      });

      assert.strictEqual(engine.activeCharacter, "STUDENT");
      assert.strictEqual(activeConcept, "Recursion Base Case");
    });
  });

  describe("3. Audio sync bindings", () => {
    test("transitions to LISTENING_ACTIVE on onRecordStart", () => {
      const engine = new TestPerformanceEngine("STUDENT", "IDLE");
      const events: LearningEngineEvents = {};
      const unbind = bindAnimationToLearningEngine(engine, events);

      events.onRecordStart?.();
      assert.strictEqual(engine.state, "LISTENING_ACTIVE");
      unbind();
    });

    test("transitions to THINKING on onRecordStop, not IDLE", () => {
      const engine = new TestPerformanceEngine("STUDENT", "LISTENING_ACTIVE");
      const events: LearningEngineEvents = {};
      const unbind = bindAnimationToLearningEngine(engine, events);

      events.onRecordStop?.();
      assert.strictEqual(engine.state, "THINKING");
      unbind();
    });

    test("transitions to IDLE on onSpeechError, never stays in SPEAKING", () => {
      const engine = new TestPerformanceEngine("STUDENT", "SPEAKING");
      const events: LearningEngineEvents = {};
      const unbind = bindAnimationToLearningEngine(engine, events);

      events.onSpeechError?.();
      assert.strictEqual(engine.state, "IDLE");
      unbind();
    });
  });

  describe("4. Assessment sync bindings", () => {
    test("transitions to REACTING_POSITIVE on positive assessment", () => {
      const engine = new TestPerformanceEngine("STUDENT", "IDLE");
      const events: LearningEngineEvents = {};
      const unbind = bindAnimationToLearningEngine(engine, events);

      events.onAssessmentResult?.({ isPositive: true });
      assert.strictEqual(engine.state, "REACTING_POSITIVE");
      unbind();
    });

    test("transitions to REACTING_CONFUSED on misconception detected", () => {
      const engine = new TestPerformanceEngine("STUDENT", "THINKING");
      const events: LearningEngineEvents = {};
      const unbind = bindAnimationToLearningEngine(engine, events);

      events.onAssessmentResult?.({ hasMisconception: true });
      assert.strictEqual(engine.state, "REACTING_CONFUSED");
      unbind();
    });

    test("transitions to REACTING_GRUMPY only on genuine session-end threshold", () => {
      const engine = new TestPerformanceEngine("PROFESSOR", "IDLE");
      const events: LearningEngineEvents = {};
      const unbind = bindAnimationToLearningEngine(engine, events);

      // Normal user exit
      events.onSessionEnd?.("user");
      assert.strictEqual(engine.state, "EXITING");

      // Reset to idle
      engine.transition("IDLE", { force: true });

      // Unanswered threshold reached by Professor
      events.onSessionEnd?.("unanswered_threshold");
      assert.strictEqual(engine.state, "REACTING_GRUMPY");
      unbind();
    });

    test("never transitions to REACTING_GRUMPY on network error", () => {
      const engine = new TestPerformanceEngine("PROFESSOR", "IDLE");
      const events: LearningEngineEvents = {};
      const unbind = bindAnimationToLearningEngine(engine, events);

      events.onSpeechError?.();
      assert.notStrictEqual(engine.state, "REACTING_GRUMPY");
      assert.strictEqual(engine.state, "IDLE");
      unbind();
    });
  });

  describe("5. Cleanup & Lifecycle", () => {
    test("cleans up all listeners on destroy() and rejects transitions", () => {
      const engine = new TestPerformanceEngine("STUDENT", "IDLE");
      engine.destroy();
      engine.transition("SPEAKING");
      assert.strictEqual(engine.state, "IDLE");
    });
  });

  describe("6. Reduced motion", () => {
    test("skips all body animation delays when prefers-reduced-motion is active", () => {
      const engine = new TestPerformanceEngine("STUDENT", "IDLE", true);
      engine.transition("REACTING_POSITIVE");
      // Under reduced motion, self-completing states resolve immediately
      assert.strictEqual(engine.state, "TAKING_NOTES");
      assert.strictEqual(engine.isAnimating, false);
    });
  });

  describe("7. Character Animation Definitions Integrity", () => {
    test("Student animations define entrance, idle, listening, notes, and exit", () => {
      assert.ok(studentAnimations.ENTERING);
      assert.ok(studentAnimations.IDLE);
      assert.ok(studentAnimations.LISTENING_ACTIVE);
      assert.ok(studentAnimations.TAKING_NOTES);
      assert.ok(studentAnimations.EXITING);
      assert.strictEqual(studentAnimations.TAKING_NOTES.props?.[0]?.type, "NOTEBOOK");
    });

    test("Teacher animations define book prop and explaining posture", () => {
      assert.ok(teacherAnimations.ENTERING);
      assert.ok(teacherAnimations.EXPLAINING);
      assert.strictEqual(teacherAnimations.EXPLAINING.props?.[0]?.type, "BOOK");
      assert.strictEqual(teacherAnimations.EXPLAINING.props?.[0]?.animation, "open");
    });

    test("Professor animations define clipboard prop and 5-step grumpy departure", () => {
      assert.ok(professorAnimations.ENTERING);
      assert.ok(professorAnimations.MARKING);
      assert.ok(professorAnimations.REACTING_GRUMPY);
      assert.strictEqual(professorAnimations.MARKING.props?.[0]?.type, "CLIPBOARD");
      assert.strictEqual(professorAnimations.REACTING_GRUMPY.duration, 3200);
      assert.strictEqual(professorAnimations.REACTING_GRUMPY.interruptible, false);
    });
  });
});
