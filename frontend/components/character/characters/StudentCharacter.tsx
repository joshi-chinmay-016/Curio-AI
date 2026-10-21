"use client";

import React, { useState, useEffect, useMemo } from "react";
import { motion, Variants } from "framer-motion";
import { PerformanceState, CharacterComponentProps } from "../types";

// ==========================================
// ANIMATION VARIANTS
// ==========================================

const headVariants: Variants = {
  IDLE: {
    rotate: 0,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 80, damping: 12 },
  },
  LISTENING: {
    rotate: -4,
    y: -3,
    scale: 1.02,
    transition: { type: "spring", stiffness: 160, damping: 14 },
  },
  LISTENING_ACTIVE: {
    rotate: -4,
    y: -3,
    scale: 1.02,
    transition: { type: "spring", stiffness: 160, damping: 14 },
  },
  LISTENING_IDLE: {
    rotate: -2,
    y: -1,
    scale: 1.01,
    transition: { type: "spring", stiffness: 120, damping: 14 },
  },
  THINKING: {
    rotate: [0, 6, 4, 6, 4],
    y: [-3, -7, -6, -7, -5],
    transition: {
      duration: 2,
      repeat: Infinity,
      repeatType: "mirror",
      ease: "easeInOut",
    },
  },
  SPEAKING: {
    rotate: [-1, 1, -0.5, 1.5, -1],
    y: [-2, -5, -3, -4, -2],
    transition: {
      duration: 1.2,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
  ASKING: {
    rotate: -6,
    y: -6,
    scale: 1.03,
    transition: { type: "spring", stiffness: 200, damping: 16 },
  },
  TAKING_NOTES: {
    rotate: 8,
    y: 12,
    transition: { type: "spring", stiffness: 120, damping: 18 },
  },
  REACTING_POSITIVE: {
    rotate: [0, -3, 2, -1, 0],
    y: [0, -10, -4, -8, 0],
    transition: {
      duration: 0.7,
      ease: [0.34, 1.56, 0.64, 1],
    },
  },
  REACTING_CONFUSED: {
    rotate: [0, -5, 3, -4, 2, 0],
    transition: { duration: 0.8, ease: "easeInOut" },
  },
  ENTERING: {
    x: [-80, 0],
    opacity: [0, 1],
    transition: { duration: 0.8, ease: [0.25, 0.1, 0.25, 1] },
  },
  EXITING: {
    x: [0, 80],
    opacity: [1, 0],
    transition: { duration: 0.6, ease: [0.55, 0, 1, 0.45] },
  },
};

const bodyVariants: Variants = {
  IDLE: {
    y: [0, -2, 0],
    rotate: 0,
    x: 0,
    transition: { duration: 4, repeat: Infinity, ease: "easeInOut" },
  },
  LISTENING: {
    x: 4,
    y: 0,
    rotate: -1.5,
    transition: { type: "spring", stiffness: 150, damping: 16 },
  },
  LISTENING_ACTIVE: {
    x: 4,
    y: 0,
    rotate: -1.5,
    transition: { type: "spring", stiffness: 150, damping: 16 },
  },
  LISTENING_IDLE: {
    x: 2,
    y: 0,
    rotate: -0.8,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  TAKING_NOTES: {
    rotate: 4,
    y: 8,
    x: 0,
    transition: { type: "spring", stiffness: 110, damping: 16 },
  },
  ASKING: {
    x: 5,
    y: -4,
    rotate: -2,
    transition: { type: "spring", stiffness: 180, damping: 18 },
  },
  SPEAKING: {
    y: [0, -2, 0],
    rotate: 0,
    x: 0,
    transition: { duration: 2, repeat: Infinity, ease: "easeInOut" },
  },
  REACTING_POSITIVE: {
    y: [0, -8, 0],
    rotate: 0,
    x: 0,
    transition: { duration: 0.7, ease: [0.34, 1.56, 0.64, 1] },
  },
  REACTING_CONFUSED: {
    rotate: [0, -2, 1, 0],
    y: [0, -2, 0],
    transition: { duration: 0.8, ease: "easeInOut" },
  },
};

const rightArmVariants: Variants = {
  IDLE: {
    rotate: 0,
    x: 0,
    y: 0,
    transition: { type: "spring", stiffness: 100, damping: 14 },
  },
  TAKING_NOTES: {
    rotate: [0, 18, 12, 18, 14, 18],
    x: [0, 6, 4, 6, 4, 6],
    y: [0, 4, 2, 4, 2, 4],
    transition: {
      duration: 0.8,
      repeat: Infinity,
      repeatType: "mirror",
      ease: "easeInOut",
    },
  },
  ASKING: {
    rotate: -25,
    x: -3,
    y: -8,
    transition: { type: "spring", stiffness: 200, damping: 15 },
  },
  SPEAKING: {
    rotate: [-5, -16, -6, -12, -5],
    x: 0,
    y: 0,
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

const leftArmVariants: Variants = {
  IDLE: {
    rotate: 0,
    x: 0,
    y: 0,
    transition: { type: "spring", stiffness: 100, damping: 14 },
  },
  LISTENING: {
    rotate: 2,
    transition: { type: "spring", stiffness: 120, damping: 14 },
  },
  LISTENING_ACTIVE: {
    rotate: 2,
    transition: { type: "spring", stiffness: 120, damping: 14 },
  },
  TAKING_NOTES: {
    rotate: -12,
    x: 8,
    y: 6,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  SPEAKING: {
    rotate: [0, 6, 0, 4, 0],
    transition: { duration: 2, repeat: Infinity, ease: "easeInOut" },
  },
};

export const StudentCharacter = ({
  performance,
  prefersReducedMotion = false,
}: CharacterComponentProps) => {
  // Eye Blink state
  const [blink, setBlink] = useState(false);

  useEffect(() => {
    if (prefersReducedMotion) return;
    let timer: NodeJS.Timeout;

    const scheduleBlink = () => {
      const delay = 3000 + Math.random() * 2000;
      timer = setTimeout(() => {
        setBlink(true);
        setTimeout(() => {
          setBlink(false);
          scheduleBlink();
        }, 150);
      }, delay);
    };

    scheduleBlink();
    return () => clearTimeout(timer);
  }, [prefersReducedMotion]);

  // Expression Mapping
  const expression = useMemo(() => {
    switch (performance) {
      case "SPEAKING":
        return {
          mouth: "M 92 73 Q 100 83 108 73 Q 100 76 92 73", // open speaking
          brows: "neutral",
        };
      case "ASKING":
        return {
          mouth: "M 93 74 L 107 74",
          brows: "raised",
        };
      case "THINKING":
        return {
          mouth: "M 94 74 L 106 74",
          brows: "furrowed",
        };
      case "REACTING_POSITIVE":
        return {
          mouth: "M 90 71 Q 100 81 110 71", // big smile
          brows: "raised",
        };
      case "REACTING_CONFUSED":
        return {
          mouth: "M 93 76 Q 100 69 107 76", // confused frown
          brows: "furrowed",
        };
      case "TAKING_NOTES":
        return {
          mouth: "M 93 74 Q 100 78 107 74",
          brows: "focused",
        };
      case "LISTENING":
      case "LISTENING_ACTIVE":
      case "LISTENING_IDLE":
        return {
          mouth: "M 93 73 Q 100 78 107 73",
          brows: "neutral",
        };
      case "IDLE":
      default:
        return {
          mouth: "M 91 72 Q 100 80 109 72", // gentle smile
          brows: "neutral",
        };
    }
  }, [performance]);

  // Current normalized animation state
  const animKey = prefersReducedMotion ? "IDLE" : performance;

  return (
    <div className="relative w-full h-full flex items-center justify-center select-none">
      <svg
        viewBox="0 0 200 320"
        width="100%"
        height="100%"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full object-contain filter drop-shadow-2xl"
      >
        <defs>
          {/* Skin Gradients */}
          <radialGradient id="stdSkinGlow" cx="50%" cy="38%" r="62%">
            <stop offset="0%" stopColor="#FFF1E8" />
            <stop offset="55%" stopColor="#FBD3B6" />
            <stop offset="100%" stopColor="#E69F7C" />
          </radialGradient>
          <linearGradient id="stdNeckShadow" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#DB9672" />
            <stop offset="100%" stopColor="#FBD3B6" />
          </linearGradient>

          {/* Hair Gradient */}
          <linearGradient id="stdHairGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#6E4424" />
            <stop offset="45%" stopColor="#52321A" />
            <stop offset="100%" stopColor="#382010" />
          </linearGradient>

          {/* Shirt Gradients */}
          <linearGradient id="stdShirtGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6694B3" />
            <stop offset="25%" stopColor="#82ADCC" />
            <stop offset="75%" stopColor="#82ADCC" />
            <stop offset="100%" stopColor="#5B87A6" />
          </linearGradient>
          <linearGradient id="stdInnerShirt" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1B222A" />
            <stop offset="100%" stopColor="#28323E" />
          </linearGradient>

          {/* Pants Gradient */}
          <linearGradient id="stdPantsGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#334052" />
            <stop offset="100%" stopColor="#1E2632" />
          </linearGradient>

          {/* Eye Iris Gradient */}
          <radialGradient id="stdIrisGrad" cx="38%" cy="38%" r="65%">
            <stop offset="0%" stopColor="#6E3F1F" />
            <stop offset="55%" stopColor="#4D2A14" />
            <stop offset="100%" stopColor="#241105" />
          </radialGradient>
        </defs>

        {/* ========================================================
            LAYER 1: BACKPACK (stays mostly static behind body)
            ======================================================== */}
        <g id="student-backpack">
          <rect x="66" y="110" width="68" height="70" rx="16" fill="#181F26" />
          <path d="M 64 120 Q 60 146 64 168 L 72 168 L 70 120 Z" fill="#222B35" />
          <path d="M 136 120 Q 140 146 136 168 L 128 168 L 130 120 Z" fill="#222B35" />
        </g>

        {/* ========================================================
            LAYER 6: LEGS & SHOES (Static foundation)
            ======================================================== */}
        <g id="student-legs">
          {/* Left Leg (viewer's left) */}
          <path
            d="M 83 186 L 79 276 L 94 276 L 97 186 Z"
            fill="url(#stdPantsGrad)"
          />
          {/* Right Leg (viewer's right) */}
          <path
            d="M 103 186 L 106 276 L 121 276 L 117 186 Z"
            fill="url(#stdPantsGrad)"
          />
          {/* Jeans Crotch & Seam */}
          <path d="M 97 186 Q 100 200 103 186" stroke="#141920" strokeWidth="1.5" fill="none" />
          <line x1="86" y1="230" x2="86" y2="276" stroke="#25303E" strokeWidth="1" />
          <line x1="114" y1="230" x2="114" y2="276" stroke="#25303E" strokeWidth="1" />

          {/* Left Sneaker */}
          <path
            d="M 74 278 Q 78 272 90 274 L 95 284 L 72 284 Z"
            fill="#272F3A"
          />
          <rect x="71" y="284" width="25" height="5" rx="2" fill="#E5E7EB" />
          <path d="M 71 281 Q 74 278 78 284" fill="#E5E7EB" />

          {/* Right Sneaker */}
          <path
            d="M 126 278 Q 122 272 110 274 L 105 284 L 128 284 Z"
            fill="#272F3A"
          />
          <rect x="104" y="284" width="25" height="5" rx="2" fill="#E5E7EB" />
          <path d="M 129 281 Q 126 278 122 284" fill="#E5E7EB" />
        </g>

        {/* ========================================================
            LAYER 2: BODY (Blue Shirt, Torso, Neck) with breathing
            ======================================================== */}
        <motion.g
          id="student-body"
          variants={bodyVariants}
          animate={animKey}
          style={{ transformOrigin: "100px 186px" }}
        >
          {/* Neck */}
          <path
            d="M 93 84 L 93 104 L 107 104 L 107 84 Z"
            fill="url(#stdNeckShadow)"
          />

          {/* Inner dark t-shirt */}
          <path
            d="M 90 98 Q 100 104 110 98 L 112 186 L 88 186 Z"
            fill="url(#stdInnerShirt)"
          />

          {/* Light Blue Button-Up Overshirt - Main Torso */}
          <path
            d="M 74 100 Q 86 100 93 102 L 95 186 L 75 186 Q 73 140 74 100 Z"
            fill="url(#stdShirtGrad)"
          />
          <path
            d="M 126 100 Q 114 100 107 102 L 105 186 L 125 186 Q 127 140 126 100 Z"
            fill="url(#stdShirtGrad)"
          />

          {/* Shirt Collar */}
          <path d="M 90 98 L 84 106 L 94 107 Z" fill="#93BBD8" />
          <path d="M 110 98 L 116 106 L 106 107 Z" fill="#93BBD8" />

          {/* Buttons on placket */}
          <circle cx="100" cy="118" r="1.5" fill="#E2E8F0" />
          <circle cx="100" cy="138" r="1.5" fill="#E2E8F0" />
          <circle cx="100" cy="158" r="1.5" fill="#E2E8F0" />

          {/* Backpack Straps across shoulders */}
          <path
            d="M 79 100 L 77 182 L 83 182 L 85 100 Z"
            fill="#222A34"
          />
          <rect x="78" y="132" width="6" height="3" fill="#64748B" rx="1" />
          <path
            d="M 121 100 L 123 182 L 117 182 L 115 100 Z"
            fill="#222A34"
          />
          <rect x="116" y="132" width="6" height="3" fill="#64748B" rx="1" />

          {/* Neck Headphones (resting around collar) */}
          <path
            d="M 87 94 Q 100 103 113 94"
            stroke="#181E26"
            strokeWidth="4"
            fill="none"
            strokeLinecap="round"
          />
          <ellipse cx="87" cy="94" rx="4" ry="6" fill="#242C37" />
          <ellipse cx="113" cy="94" rx="4" ry="6" fill="#242C37" />
        </motion.g>

        {/* ========================================================
            LAYER 3: LEFT ARM (Viewer's left)
            ======================================================== */}
        <motion.g
          id="student-left-arm"
          variants={leftArmVariants}
          animate={animKey}
          style={{ transformOrigin: "75px 104px" }}
        >
          {/* Blue sleeve */}
          <path
            d="M 76 100 Q 66 106 68 126 L 77 124 Q 78 110 76 100 Z"
            fill="url(#stdShirtGrad)"
          />
          {/* Forearm & Hand */}
          <path
            d="M 68 126 L 65 168 Q 65 174 68 178 L 74 176 L 76 124 Z"
            fill="#FBD3B6"
          />
          <ellipse cx="68" cy="180" rx="4.5" ry="6" fill="#FBD3B6" />
        </motion.g>

        {/* ========================================================
            LAYER 4 & 5: RIGHT ARM & HAND (Primary Gesture Arm)
            ======================================================== */}
        <motion.g
          id="student-right-arm"
          variants={rightArmVariants}
          animate={animKey}
          style={{ transformOrigin: "125px 104px" }}
        >
          {/* Blue sleeve */}
          <path
            d="M 124 100 Q 134 106 132 126 L 123 124 Q 122 110 124 100 Z"
            fill="url(#stdShirtGrad)"
          />
          {/* Forearm */}
          <path
            d="M 132 126 L 135 168 Q 135 174 132 178 L 126 176 L 124 124 Z"
            fill="#FBD3B6"
          />
          <ellipse cx="132" cy="180" rx="4.5" ry="6" fill="#FBD3B6" />

          {/* Stylus / Pen when taking notes */}
          {performance === "TAKING_NOTES" && (
            <path
              d="M 132 178 L 114 206 L 111 204 L 129 176 Z"
              fill="#0F2B4A"
              stroke="#3A63FF"
              strokeWidth="1.2"
            />
          )}
        </motion.g>

        {/* ========================================================
            LAYER 7, 8, 9, 10: HEAD, HAIR, HEADPHONES & FACE
            ======================================================== */}
        <motion.g
          id="student-head-group"
          variants={headVariants}
          animate={animKey}
          style={{ transformOrigin: "100px 92px" }}
        >
          {/* Head Base Skin */}
          <ellipse cx="100" cy="62" rx="30" ry="32" fill="url(#stdSkinGlow)" />
          {/* Chin refinement */}
          <path
            d="M 75 66 Q 84 92 100 92 Q 116 92 125 66 Z"
            fill="url(#stdSkinGlow)"
          />

          {/* Ears */}
          <ellipse cx="70" cy="63" rx="4.5" ry="7.5" fill="#FBD3B6" />
          <ellipse cx="70" cy="63" rx="2.5" ry="4.5" fill="#DB9B77" />
          <ellipse cx="130" cy="63" rx="4.5" ry="7.5" fill="#FBD3B6" />
          <ellipse cx="130" cy="63" rx="2.5" ry="4.5" fill="#DB9B77" />

          {/* Cheeks Blush */}
          <circle cx="83" cy="68" r="6" fill="#F5AB90" opacity="0.45" />
          <circle cx="117" cy="68" r="6" fill="#F5AB90" opacity="0.45" />

          {/* Soft rounded nose */}
          <path
            d="M 97 59 Q 100 66 103 59"
            stroke="#D88F6D"
            strokeWidth="1.8"
            strokeLinecap="round"
            fill="none"
          />

          {/* --- FACE: LARGE EXPRESSIVE PIXAR-STYLE EYES --- */}
          <g
            id="student-eyes"
            style={{
              transformOrigin: "100px 56px",
              transform: blink ? "scaleY(0.1)" : "scaleY(1)",
              transition: "transform 0.15s ease-in-out",
            }}
          >
            {/* Left Eye */}
            <ellipse cx="87" cy="55" rx="8" ry="9.5" fill="#FFFFFF" />
            <circle cx="87" cy="55" r="6.2" fill="url(#stdIrisGrad)" />
            <circle cx="87" cy="55" r="3.2" fill="#0E1724" />
            <circle cx="89" cy="53" r="1.8" fill="#FFFFFF" /> {/* Catchlight */}
            <circle cx="85" cy="57" r="0.8" fill="#FFFFFF" opacity="0.6" />
            {/* Upper eyelash line */}
            <path d="M 79 53 Q 87 47 95 53" stroke="#361E10" strokeWidth="1.8" fill="none" strokeLinecap="round" />

            {/* Right Eye */}
            <ellipse cx="113" cy="55" rx="8" ry="9.5" fill="#FFFFFF" />
            <circle cx="113" cy="55" r="6.2" fill="url(#stdIrisGrad)" />
            <circle cx="113" cy="55" r="3.2" fill="#0E1724" />
            <circle cx="115" cy="53" r="1.8" fill="#FFFFFF" /> {/* Catchlight */}
            <circle cx="111" cy="57" r="0.8" fill="#FFFFFF" opacity="0.6" />
            {/* Upper eyelash line */}
            <path d="M 105 53 Q 113 47 121 53" stroke="#361E10" strokeWidth="1.8" fill="none" strokeLinecap="round" />
          </g>

          {/* Eyebrows */}
          <g id="student-eyebrows">
            {expression.brows === "raised" ? (
              <>
                <path d="M 79 43 Q 87 38 95 43" stroke="#4A2E1B" strokeWidth="2.8" strokeLinecap="round" fill="none" />
                <path d="M 105 43 Q 113 38 121 43" stroke="#4A2E1B" strokeWidth="2.8" strokeLinecap="round" fill="none" />
              </>
            ) : expression.brows === "furrowed" ? (
              <>
                <path d="M 80 46 Q 87 49 95 44" stroke="#4A2E1B" strokeWidth="2.8" strokeLinecap="round" fill="none" />
                <path d="M 105 44 Q 113 49 120 46" stroke="#4A2E1B" strokeWidth="2.8" strokeLinecap="round" fill="none" />
              </>
            ) : expression.brows === "focused" ? (
              <>
                <path d="M 80 47 L 95 47" stroke="#4A2E1B" strokeWidth="2.6" strokeLinecap="round" />
                <path d="M 105 47 L 120 47" stroke="#4A2E1B" strokeWidth="2.6" strokeLinecap="round" />
              </>
            ) : (
              <>
                <path d="M 79 45 Q 87 41 95 45" stroke="#4A2E1B" strokeWidth="2.8" strokeLinecap="round" fill="none" />
                <path d="M 105 45 Q 113 41 121 45" stroke="#4A2E1B" strokeWidth="2.8" strokeLinecap="round" fill="none" />
              </>
            )}
          </g>

          {/* Mouth */}
          <path
            d={expression.mouth}
            stroke="#9E4D3B"
            strokeWidth="2.4"
            strokeLinecap="round"
            fill={performance === "SPEAKING" ? "#9E4D3B" : "none"}
          />

          {/* --- LAYER 8: HAIR (Tousled Brown Locks matching reference) --- */}
          <g id="student-hair">
            <path
              d="M 69 58 Q 63 26 92 20 Q 110 16 128 24 Q 137 36 131 58 Q 126 36 108 30 Q 88 28 69 58 Z"
              fill="url(#stdHairGrad)"
            />
            {/* Volume crests and fringe */}
            <path
              d="M 78 30 Q 72 18 86 16 Q 98 16 96 28 Z"
              fill="#6E4424"
            />
            <path
              d="M 94 26 Q 106 14 118 20 Q 124 26 114 34 Z"
              fill="#6E4424"
            />
            <path
              d="M 71 44 Q 82 34 90 42 Q 97 32 107 40 Q 116 32 126 44 Q 116 34 102 32 Q 86 34 71 44 Z"
              fill="#52321A"
            />
          </g>

          {/* --- LAYER 9: HEADPHONES (Over-Ear Sleek Design) --- */}
          <g id="student-headphones">
            {/* Headband arching over hair */}
            <path
              d="M 68 56 Q 68 14 100 14 Q 132 14 132 56"
              stroke="#242C37"
              strokeWidth="6"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d="M 74 46 Q 74 20 100 20 Q 126 20 126 46"
              stroke="#151A21"
              strokeWidth="3"
              fill="none"
              strokeLinecap="round"
            />

            {/* Left Earcup */}
            <ellipse cx="67" cy="56" rx="7" ry="14" fill="#242C37" />
            <ellipse cx="67" cy="56" rx="4.5" ry="10" fill="#151A21" />
            <circle cx="67" cy="56" r="2.5" fill="#828E9E" />

            {/* Right Earcup */}
            <ellipse cx="133" cy="56" rx="7" ry="14" fill="#242C37" />
            <ellipse cx="133" cy="56" rx="4.5" ry="10" fill="#151A21" />
            <circle cx="133" cy="56" r="2.5" fill="#828E9E" />
          </g>
        </motion.g>

        {/* ========================================================
            LAYER 11: NOTEBOOK PROP (Appears in TAKING_NOTES)
            ======================================================== */}
        {performance === "TAKING_NOTES" && (
          <motion.g
            id="student-notebook-layer"
            initial={{ opacity: 0, y: 30, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ type: "spring", stiffness: 220, damping: 18 }}
          >
            {/* Notebook Glow */}
            <ellipse cx="100" cy="214" rx="46" ry="34" fill="#3A63FF" opacity="0.18" filter="blur(8px)" />

            {/* Notebook Hardcover */}
            <rect
              x="56"
              y="180"
              width="88"
              height="64"
              rx="5"
              fill="#FFFFFF"
              stroke="#0F2B4A"
              strokeWidth="2.2"
            />
            {/* Binding strip */}
            <rect x="56" y="180" width="88" height="12" rx="4" fill="#F1F5F9" />

            {/* Spiral Rings */}
            {[62, 70, 78, 86, 94, 102, 110, 118, 126, 134, 140].map((x) => (
              <circle
                key={x}
                cx={x}
                cy="186"
                r="3"
                fill="none"
                stroke="#64748B"
                strokeWidth="1.5"
              />
            ))}

            {/* Animated Writing Lines */}
            {[200, 210, 220, 230].map((y, i) => (
              <motion.line
                key={y}
                x1="64"
                y1={y}
                x2="136"
                y2={y}
                stroke="#0F2B4A"
                strokeWidth="1.6"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{
                  delay: i * 0.35,
                  duration: 0.45,
                  repeat: Infinity,
                  repeatDelay: 1.8,
                  ease: "easeOut",
                }}
              />
            ))}
          </motion.g>
        )}

        {/* ========================================================
            LAYER 12: THOUGHT BUBBLE (Appears in THINKING)
            ======================================================== */}
        {performance === "THINKING" && (
          <motion.g
            id="student-thought-bubble"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            style={{ transformOrigin: "125px 50px" }}
            transition={{ type: "spring", stiffness: 280, damping: 18 }}
          >
            <circle cx="128" cy="46" r="3.5" fill="#E8EEF3" stroke="#94A3B8" strokeWidth="1" />
            <circle cx="138" cy="38" r="5" fill="#E8EEF3" stroke="#94A3B8" strokeWidth="1" />
            <circle cx="150" cy="28" r="8" fill="#E8EEF3" stroke="#94A3B8" strokeWidth="1" />

            <rect
              x="122"
              y="4"
              width="60"
              height="28"
              rx="9"
              fill="#FFFFFF"
              stroke="#94A3B8"
              strokeWidth="1.6"
            />
            {[136, 150, 164].map((x, i) => (
              <motion.circle
                key={x}
                cx={x}
                cy="18"
                r="3"
                fill="#3A63FF"
                animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.25, 0.8] }}
                transition={{
                  duration: 1.2,
                  delay: i * 0.3,
                  repeat: Infinity,
                }}
              />
            ))}
          </motion.g>
        )}

        {/* ========================================================
            QUESTION MARK OVERLAYS (ASKING & REACTING_CONFUSED)
            ======================================================== */}
        {(performance === "ASKING" || performance === "REACTING_CONFUSED") && (
          <motion.text
            x="148"
            y="36"
            fontFamily="system-ui, -apple-system, sans-serif"
            fontSize="32"
            fontWeight="bold"
            fill={performance === "REACTING_CONFUSED" ? "#FF6B1A" : "#3A63FF"}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 15 }}
            style={{ transformOrigin: "148px 36px" }}
          >
            ?
          </motion.text>
        )}
      </svg>
    </div>
  );
};
