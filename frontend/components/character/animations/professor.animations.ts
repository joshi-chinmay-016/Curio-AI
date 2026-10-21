import { AnimationDefinition } from "@/types/performanceEngine";

export const professorEntrance: AnimationDefinition = {
  id: "professor-entrance",
  character: "PROFESSOR",
  performanceState: "ENTERING",
  duration: 1000,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateX: [70, 30, 8, 0],
    translateY: [4, -2, 1, 0],
    rotate: [0.5, -0.3, 0.3, 0],
    opacity: [0, 1, 1, 1],
    times: [0, 0.25, 0.75, 1],
    transition: { type: "tween", ease: [0.4, 0, 0.2, 1] },
  },
  props: [
    {
      type: "CLIPBOARD",
      enterWith: "character",
      position: "held-front",
    },
  ],
  onComplete: "IDLE",
};

export const professorIdle: AnimationDefinition = {
  id: "professor-idle",
  character: "PROFESSOR",
  performanceState: "IDLE",
  duration: 4500,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -6, 0],
    rotate: [0, 0.6, 0],
    scale: [1, 1.018, 1],
    times: [0, 0.5, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 3.8,
    },
  },
  props: [
    {
      type: "CLIPBOARD",
      position: "held-front",
    },
  ],
};

export const professorAsking: AnimationDefinition = {
  id: "professor-asking",
  character: "PROFESSOR",
  performanceState: "ASKING",
  duration: 400,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateY: [0, -3, -2],
    rotate: [0, -1, -0.5],
    scale: [1, 1.01, 1.01],
    transition: { type: "spring", stiffness: 180, damping: 20 },
  },
  props: [
    {
      type: "CLIPBOARD",
      animation: "lift",
      position: "raised",
      duration: 300,
    },
  ],
  onComplete: "LISTENING_ACTIVE",
};

export const professorListening: AnimationDefinition = {
  id: "professor-listening",
  character: "PROFESSOR",
  performanceState: "LISTENING_ACTIVE",
  duration: 2500,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -5, -1, -4, 0],
    rotate: [0, -1.2, 0.4, -0.8, 0],
    scale: [1, 1.018, 1.008, 1.015, 1],
    times: [0, 0.25, 0.5, 0.75, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 2.5,
    },
  },
  props: [
    {
      type: "CLIPBOARD",
      position: "held-front",
    },
  ],
  onComplete: "LISTENING_ACTIVE",
};

export const professorMarking: AnimationDefinition = {
  id: "professor-marking",
  character: "PROFESSOR",
  performanceState: "MARKING",
  duration: 1800,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [2, 8, 4, 7, 2],
    rotate: [0.5, 2, 1, 2, 0.5],
    times: [0, 0.25, 0.5, 0.75, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 1.4,
    },
  },
  props: [
    {
      type: "CLIPBOARD",
      position: "raised",
      sequence: [
        { action: "lift", duration: 300 },
        { action: "mark", duration: 600, markType: "check-or-cross" },
        { action: "hold", duration: 400 },
        { action: "lower", duration: 500 },
      ],
    },
  ],
};

export const professorStrict: AnimationDefinition = {
  id: "professor-strict",
  character: "PROFESSOR",
  performanceState: "REACTING_STRICT",
  duration: 800,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    rotate: [0, -2, -1.5, -2, 0],
    translateY: [0, -3, -2, -3, -1],
    times: [0, 0.2, 0.45, 0.7, 1],
    transition: { type: "tween", ease: "easeInOut" },
  },
  props: [
    {
      type: "CLIPBOARD",
      position: "held-front",
    },
  ],
  onComplete: "SPEAKING",
};

export const professorPositive: AnimationDefinition = {
  id: "professor-positive",
  character: "PROFESSOR",
  performanceState: "REACTING_POSITIVE",
  duration: 700,
  loop: false,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -5, 0, -2, 0],
    rotate: [0, 1, 0],
    times: [0, 0.3, 0.6, 0.8, 1],
    transition: { type: "spring", stiffness: 240, damping: 18 },
  },
  props: [
    {
      type: "CLIPBOARD",
      position: "held-front",
    },
  ],
  onComplete: "IDLE",
};

export const professorSpeaking: AnimationDefinition = {
  id: "professor-speaking",
  character: "PROFESSOR",
  performanceState: "SPEAKING",
  duration: 1400,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [-1, -9, -1],
    rotate: [-0.8, 0.8, -0.8],
    scale: [1.01, 1.035, 1.01],
    times: [0, 0.5, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 1.3,
    },
  },
  props: [
    {
      type: "CLIPBOARD",
      position: "held-front",
    },
  ],
};

export const professorGrumpyExit: AnimationDefinition = {
  id: "professor-grumpy-exit",
  character: "PROFESSOR",
  performanceState: "REACTING_GRUMPY",
  duration: 3200,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    rotate: [0, -2, -1.5, -8, -8, -8],
    translateX: [0, 1, 0, 2, 30, 100],
    translateY: [0, -2, 0, 0, 4, 10],
    opacity: [1, 1, 1, 1, 1, 0],
    times: [0, 0.12, 0.2, 0.35, 0.55, 1],
    transition: { type: "tween", ease: [0.4, 0, 0.8, 0.4], duration: 3.2 },
  },
  props: [
    {
      type: "CLIPBOARD",
      animation: "slam-close",
      triggerAt: 700,
      duration: 300,
      position: "lowered",
    },
  ],
  onComplete: "OFFSTAGE",
};

export const professorAnimations: Record<string, AnimationDefinition> = {
  ENTERING: professorEntrance,
  IDLE: professorIdle,
  ASKING: professorAsking,
  LISTENING_ACTIVE: professorListening,
  LISTENING_IDLE: professorListening,
  MARKING: professorMarking,
  REACTING_STRICT: professorStrict,
  REACTING_POSITIVE: professorPositive,
  REACTING_GRUMPY: professorGrumpyExit,
  SPEAKING: professorSpeaking,
  EXITING: professorGrumpyExit,
};
