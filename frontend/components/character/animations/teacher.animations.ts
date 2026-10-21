import { AnimationDefinition } from "@/types/performanceEngine";

export const teacherEntrance: AnimationDefinition = {
  id: "teacher-entrance",
  character: "TEACHER",
  performanceState: "ENTERING",
  duration: 700,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateX: [60, 20, 5, 0],
    translateY: [8, -3, 1, 0],
    rotate: [1, -0.5, 0.5, 0],
    opacity: [0, 0.9, 1, 1],
    times: [0, 0.3, 0.7, 1],
    transition: { type: "tween", ease: [0.25, 0.1, 0.25, 1] },
  },
  props: [
    {
      type: "BOOK",
      enterWith: "character",
      position: "held-left",
    },
  ],
  onComplete: "IDLE",
};

export const teacherIdle: AnimationDefinition = {
  id: "teacher-idle",
  character: "TEACHER",
  performanceState: "IDLE",
  duration: 3500,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -8, 0],
    rotate: [0, 0.8, 0],
    scale: [1, 1.02, 1],
    times: [0, 0.5, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 3.5,
    },
  },
  props: [
    {
      type: "BOOK",
      position: "held-left",
    },
  ],
};

export const teacherExplaining: AnimationDefinition = {
  id: "teacher-explaining",
  character: "TEACHER",
  performanceState: "EXPLAINING",
  duration: 500,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateY: [0, -4, -3],
    rotate: [0, -1.5, -1],
    scale: [1, 1.02, 1.015],
    times: [0, 0.4, 1],
    transition: { type: "spring", stiffness: 160, damping: 18 },
  },
  props: [
    {
      type: "BOOK",
      animation: "open",
      duration: 400,
      position: "held-left",
    },
  ],
};

export const teacherAskingVerification: AnimationDefinition = {
  id: "teacher-asking-verification",
  character: "TEACHER",
  performanceState: "ASKING",
  duration: 400,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateX: [0, 4],
    translateY: [0, -3],
    rotate: [0, -2],
    transition: { type: "spring", stiffness: 200, damping: 20 },
  },
  props: [
    {
      type: "BOOK",
      position: "held-left",
    },
  ],
  overlays: [
    {
      type: "QUESTION_MARK",
      position: "above-head",
      color: "#3A63FF",
      animation: "pop-in",
      size: 20,
    },
  ],
  onComplete: "LISTENING_ACTIVE",
};

export const teacherListening: AnimationDefinition = {
  id: "teacher-listening",
  character: "TEACHER",
  performanceState: "LISTENING_ACTIVE",
  duration: 2400,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [0, -6, -1, -5, 0],
    rotate: [0, 1.2, -0.4, 0.8, 0],
    scale: [1, 1.02, 1.01, 1.018, 1],
    times: [0, 0.25, 0.5, 0.75, 1],
    transition: {
      type: "tween",
      ease: "easeInOut",
      repeat: Infinity,
      duration: 2.4,
    },
  },
  props: [
    {
      type: "BOOK",
      position: "held-left",
    },
  ],
  onComplete: "LISTENING_ACTIVE",
};

export const teacherSpeaking: AnimationDefinition = {
  id: "teacher-speaking",
  character: "TEACHER",
  performanceState: "SPEAKING",
  duration: 1300,
  loop: true,
  interruptible: true,
  bodyAnimation: {
    translateY: [-2, -10, -2],
    rotate: [-1, 1, -1],
    scale: [1.01, 1.04, 1.01],
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
      type: "BOOK",
      animation: "open",
      position: "held-left",
    },
  ],
};

export const teacherExit: AnimationDefinition = {
  id: "teacher-exit",
  character: "TEACHER",
  performanceState: "EXITING",
  duration: 700,
  loop: false,
  interruptible: false,
  bodyAnimation: {
    translateY: [0, -4, 0, 4],
    translateX: [0, 15, 60],
    opacity: [1, 1, 0],
    times: [0, 0.2, 1],
    transition: { type: "tween", ease: [0.5, 0, 0.9, 0.5] },
  },
  props: [
    {
      type: "BOOK",
      position: "held-left",
    },
  ],
  onComplete: "OFFSTAGE",
};

export const teacherAnimations: Record<string, AnimationDefinition> = {
  ENTERING: teacherEntrance,
  IDLE: teacherIdle,
  EXPLAINING: teacherExplaining,
  ASKING: teacherAskingVerification,
  LISTENING_ACTIVE: teacherListening,
  LISTENING_IDLE: teacherListening,
  SPEAKING: teacherSpeaking,
  EXITING: teacherExit,
};
