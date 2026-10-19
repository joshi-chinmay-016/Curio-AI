import { AnimationDefinition } from "@/types/performanceEngine";

export const studentEntrance: AnimationDefinition = {
  id: "student-entrance",
  character: "STUDENT",
  performanceState: "ENTERING",
  duration: 1200,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateX: [-80, -40, -10, 0],
    translateY: [12, -4, 2, 0],
    rotate: [-1.5, 0.5, -0.5, 0],
    opacity: [0, 0.8, 1, 1],
    times: [0, 0.35, 0.75, 1],
    transition: { type: "tween", ease: [0.25, 0.1, 0.25, 1] },
  },
  onComplete: "IDLE",
};

export const studentGreetingNod: AnimationDefinition = {
  id: "student-greeting-nod",
  character: "STUDENT",
  performanceState: "IDLE",
  duration: 500,
  loop: false,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -6, 0],
    rotate: [0, 2, 0],
    times: [0, 0.4, 1],
    transition: { type: "spring", stiffness: 280, damping: 18 },
  },
};

export const studentIdle: AnimationDefinition = {
  id: "student-idle",
  character: "STUDENT",
  performanceState: "IDLE",
  duration: 3500,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -10, -2, -8, 0],
    rotate: [0, 1.2, 0, -1.2, 0],
    scale: [1, 1.025, 1, 1.02, 1],
    times: [0, 0.25, 0.5, 0.75, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 3.5,
    },
  },
};

export const studentListening: AnimationDefinition = {
  id: "student-listening",
  character: "STUDENT",
  performanceState: "LISTENING_ACTIVE",
  duration: 600,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateX: [0, 6],
    translateY: [0, -4],
    rotate: [0, -2.5],
    scale: [1, 1.02],
    transition: { type: "spring", stiffness: 180, damping: 20 },
  },
  overlays: [
    {
      type: "LISTENING_INDICATOR",
      position: "near-ear",
      animation: "pulse",
      color: "#3A63FF",
    },
  ],
  onComplete: "LISTENING_ACTIVE",
};

export const studentStopListening: AnimationDefinition = {
  id: "student-stop-listening",
  character: "STUDENT",
  performanceState: "THINKING",
  duration: 400,
  loop: false,
  interruptible: true,
  bodyAnimation: {
    translateX: [6, 2],
    translateY: [-4, -2],
    rotate: [-2.5, -1],
    transition: { type: "spring", stiffness: 200, damping: 22 },
  },
};

export const studentThinking: AnimationDefinition = {
  id: "student-thinking",
  character: "STUDENT",
  performanceState: "THINKING",
  duration: 800,
  loop: false,
  interruptible: true,
  bodyAnimation: {
    translateX: [2, 0, -2],
    translateY: [-2, -5, -4],
    rotate: [-1, 1.5, 1],
    times: [0, 0.4, 1],
    transition: { type: "tween", ease: "easeInOut" },
  },
  overlays: [
    {
      type: "THOUGHT_BUBBLE",
      position: "above-head-right",
      animation: "thinking-dots",
      delay: 200,
      duration: 600,
    },
  ],
};

export const studentTakingNotes: AnimationDefinition = {
  id: "student-taking-notes",
  character: "STUDENT",
  performanceState: "TAKING_NOTES",
  duration: 3000,
  loop: false,
  interruptible: true,
  bodyAnimation: {
    translateX: [0, 4, 3, 4, 2],
    translateY: [0, 8, 6, 8, 6],
    rotate: [0, 3, 2.5, 3, 2.5],
    times: [0, 0.15, 0.4, 0.65, 1],
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  props: [
    {
      type: "NOTEBOOK",
      enterFrom: "below",
      enterDuration: 300,
      position: "student-front",
      writingLines: {
        count: 3,
        interval: 600,
        lineColor: "#0F2B4A",
        lineWidth: "60%",
      },
      exitTo: "below",
      exitDuration: 300,
    },
  ],
  onComplete: "IDLE",
};

export const studentAsking: AnimationDefinition = {
  id: "student-asking",
  character: "STUDENT",
  performanceState: "ASKING",
  duration: 400,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateX: [0, 5],
    translateY: [0, -5],
    rotate: [0, -3],
    scale: [1, 1.03],
    transition: { type: "spring", stiffness: 220, damping: 18 },
  },
  overlays: [
    {
      type: "QUESTION_MARK",
      position: "above-head",
      animation: "pop-in",
      color: "#3A63FF",
      size: 24,
      exitOn: "state-change",
    },
  ],
};

export const studentConfused: AnimationDefinition = {
  id: "student-confused",
  character: "STUDENT",
  performanceState: "REACTING_CONFUSED",
  duration: 600,
  loop: false,
  interruptible: true,
  bodyAnimation: {
    rotate: [0, -4, 2, -3, 0],
    translateY: [0, -3, -1, -2, 0],
    times: [0, 0.2, 0.5, 0.75, 1],
    transition: { type: "tween", ease: "easeInOut" },
  },
  overlays: [
    {
      type: "QUESTION_MARK",
      position: "above-head",
      animation: "fade-in",
      color: "#FF6B1A",
      size: 20,
    },
  ],
  onComplete: "SPEAKING",
};

export const studentPositive: AnimationDefinition = {
  id: "student-positive",
  character: "STUDENT",
  performanceState: "REACTING_POSITIVE",
  duration: 700,
  loop: false,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -10, -2, -6, 0],
    rotate: [0, 1, -0.5, 0.5, 0],
    scale: [1, 1.04, 1.01, 1.02, 1],
    times: [0, 0.25, 0.5, 0.75, 1],
    transition: { type: "spring", stiffness: 300, damping: 15 },
  },
  overlays: [
    {
      type: "CHECK_MARK",
      position: "above-head",
      animation: "draw-in",
      color: "#3A63FF",
      duration: 400,
    },
  ],
  onComplete: "TAKING_NOTES",
};

export const studentSpeaking: AnimationDefinition = {
  id: "student-speaking",
  character: "STUDENT",
  performanceState: "SPEAKING",
  duration: 1200,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [-3, -12, -3, -8, -3],
    rotate: [-1.5, 1.5, -2, 1, -1.5],
    scale: [1.02, 1.05, 1.01, 1.04, 1.02],
    times: [0, 0.25, 0.5, 0.75, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 1.2,
    },
  },
};

export const studentExit: AnimationDefinition = {
  id: "student-exit",
  character: "STUDENT",
  performanceState: "EXITING",
  duration: 800,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    rotate: [0, 3, 0, -1],
    translateX: [0, 2, -20, -80],
    translateY: [0, -4, 0, 10],
    opacity: [1, 1, 1, 0],
    times: [0, 0.15, 0.6, 1],
    transition: { type: "tween", ease: [0.55, 0, 1, 0.45] },
  },
  onComplete: "OFFSTAGE",
};

export const studentAnimations: Record<string, AnimationDefinition> = {
  ENTERING: studentEntrance,
  IDLE: studentIdle,
  LISTENING_ACTIVE: studentListening,
  LISTENING_IDLE: studentIdle,
  THINKING: studentThinking,
  TAKING_NOTES: studentTakingNotes,
  ASKING: studentAsking,
  REACTING_CONFUSED: studentConfused,
  REACTING_POSITIVE: studentPositive,
  SPEAKING: studentSpeaking,
  EXITING: studentExit,
};
