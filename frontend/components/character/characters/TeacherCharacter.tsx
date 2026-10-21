"use client";

import React, { useState, useEffect, useMemo } from "react";
import { motion, Variants } from "framer-motion";
import { PerformanceState, CharacterComponentProps } from "../types";

// ==========================================
// TEACHER ANIMATION VARIANTS (Measured & Calm)
// ==========================================

const headVariants: Variants = {
  IDLE: {
    rotate: 0,
    y: 0,
    transition: { type: "spring", stiffness: 60, damping: 15 },
  },
  LISTENING: {
    rotate: -2.5,
    y: -2,
    transition: { type: "spring", stiffness: 140, damping: 16 },
  },
  LISTENING_ACTIVE: {
    rotate: -2.5,
    y: -2,
    transition: { type: "spring", stiffness: 140, damping: 16 },
  },
  LISTENING_IDLE: {
    rotate: -1,
    y: -1,
    transition: { type: "spring", stiffness: 100, damping: 16 },
  },
  EXPLAINING: {
    rotate: [-1, 1.2, -0.5, 0.8, -1],
    y: [-1, -3, -2, -3, -1],
    transition: { duration: 2, repeat: Infinity, ease: "easeInOut" },
  },
  SPEAKING: {
    rotate: [-1, 1, -0.5, 0.5, -1],
    y: [-1, -3, -2, -3, -1],
    transition: { duration: 1.8, repeat: Infinity, ease: "easeInOut" },
  },
  ASKING: {
    rotate: -3,
    y: -3,
    transition: { type: "spring", stiffness: 160, damping: 18 },
  },
  THINKING: {
    rotate: 3,
    y: -2,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  REACTING_POSITIVE: {
    rotate: [0, 2, -1, 0],
    y: [0, -4, 0],
    transition: { duration: 0.6, ease: "easeInOut" },
  },
  REACTING_CONFUSED: {
    rotate: [0, -3, 2, 0],
    transition: { duration: 0.7, ease: "easeInOut" },
  },
  ENTERING: {
    x: [80, 0],
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
    y: [0, -1.5, 0],
    rotate: 0,
    x: 0,
    transition: { duration: 4.5, repeat: Infinity, ease: "easeInOut" },
  },
  LISTENING: {
    x: -2,
    rotate: 1,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  LISTENING_ACTIVE: {
    x: -2,
    rotate: 1,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  EXPLAINING: {
    y: [0, -2, 0],
    rotate: [0, 0.8, 0],
    transition: { duration: 2.5, repeat: Infinity, ease: "easeInOut" },
  },
  SPEAKING: {
    y: [0, -2, 0],
    transition: { duration: 2, repeat: Infinity, ease: "easeInOut" },
  },
  ASKING: {
    y: -3,
    rotate: -1.5,
    transition: { type: "spring", stiffness: 150, damping: 16 },
  },
  REACTING_POSITIVE: {
    y: [0, -4, 0],
    transition: { duration: 0.6, ease: "easeOut" },
  },
};

const rightArmVariants: Variants = {
  IDLE: {
    rotate: 0,
    x: 0,
    y: 0,
    transition: { type: "spring", stiffness: 100, damping: 15 },
  },
  EXPLAINING: {
    rotate: [-12, -22, -14, -24, -12],
    x: [0, 3, 0, 3, 0],
    y: [0, -4, -2, -5, 0],
    transition: {
      duration: 2.2,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
  SPEAKING: {
    rotate: [-6, -14, -8, -16, -6],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
  ASKING: {
    rotate: -14,
    y: -2,
    transition: { type: "spring", stiffness: 160, damping: 16 },
  },
  LISTENING: {
    rotate: 2,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  LISTENING_ACTIVE: {
    rotate: 2,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
};

const leftArmVariants: Variants = {
  IDLE: {
    rotate: 4,
    y: 0,
    transition: { type: "spring", stiffness: 100, damping: 14 },
  },
  EXPLAINING: {
    rotate: -14,
    y: -10,
    x: 2,
    transition: { type: "spring", stiffness: 140, damping: 16 },
  },
  SPEAKING: {
    rotate: -8,
    y: -5,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  ASKING: {
    rotate: 4,
    y: 0,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  LISTENING: {
    rotate: 8,
    y: 4,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
  LISTENING_ACTIVE: {
    rotate: 8,
    y: 4,
    transition: { type: "spring", stiffness: 120, damping: 16 },
  },
};

export const TeacherCharacter = ({
  performance,
  prefersReducedMotion = false,
}: CharacterComponentProps) => {
  const [blink, setBlink] = useState(false);

  useEffect(() => {
    if (prefersReducedMotion) return;
    let timer: NodeJS.Timeout;

    const scheduleBlink = () => {
      const delay = 3500 + Math.random() * 2000;
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

  const expression = useMemo(() => {
    switch (performance) {
      case "EXPLAINING":
      case "SPEAKING":
        return {
          mouth: "M 93 72 Q 100 80 107 72 Q 100 75 93 72",
          brows: "neutral",
        };
      case "ASKING":
        return {
          mouth: "M 94 73 Q 100 77 106 73",
          brows: "raised",
        };
      case "THINKING":
        return {
          mouth: "M 94 74 L 106 74",
          brows: "thoughtful",
        };
      case "REACTING_POSITIVE":
        return {
          mouth: "M 91 71 Q 100 80 109 71",
          brows: "raised",
        };
      case "REACTING_CONFUSED":
        return {
          mouth: "M 94 75 Q 100 70 106 75",
          brows: "concerned",
        };
      case "IDLE":
      default:
        return {
          mouth: "M 92 72 Q 100 78 108 72",
          brows: "neutral",
        };
    }
  }, [performance]);

  const animKey = prefersReducedMotion ? "IDLE" : performance;
  const isExplaining = performance === "EXPLAINING" || performance === "SPEAKING";

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
          <radialGradient id="tchSkinGlow" cx="50%" cy="40%" r="62%">
            <stop offset="0%" stopColor="#FFF2E8" />
            <stop offset="55%" stopColor="#F8D5BF" />
            <stop offset="100%" stopColor="#E69E8A" />
          </radialGradient>
          <linearGradient id="tchNeckShadow" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#D98E7A" />
            <stop offset="100%" stopColor="#F8D5BF" />
          </linearGradient>

          {/* Hair Gradients */}
          <linearGradient id="tchHairGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#693F26" />
            <stop offset="40%" stopColor="#4D2E1B" />
            <stop offset="100%" stopColor="#321C0E" />
          </linearGradient>

          {/* Cardigan Cream Gradients */}
          <linearGradient id="tchCardiganGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#E6DFCC" />
            <stop offset="25%" stopColor="#F8F4E8" />
            <stop offset="75%" stopColor="#F8F4E8" />
            <stop offset="100%" stopColor="#DFD8C4" />
          </linearGradient>

          {/* Skirt Grey Gradients */}
          <linearGradient id="tchSkirtGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#6E6965" />
            <stop offset="100%" stopColor="#534E4A" />
          </linearGradient>

          {/* Book Leather Cover */}
          <linearGradient id="tchBookCover" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8C4E38" />
            <stop offset="100%" stopColor="#5E301F" />
          </linearGradient>
        </defs>

        {/* ========================================================
            LAYER 1: SKIRT, LEGS & SHOES (Lower body foundation)
            ======================================================== */}
        <g id="teacher-lower-body">
          {/* Pleated Midi Skirt */}
          <path
            d="M 83 172 Q 100 174 117 172 L 134 264 Q 100 268 66 264 Z"
            fill="url(#tchSkirtGrad)"
          />
          {/* Alternating Pleats */}
          {[72, 80, 88, 96, 104, 112, 120, 128].map((x, i) => (
            <line
              key={x}
              x1={85 + (x - 85) * 0.45}
              y1="173"
              x2={x}
              y2="265"
              stroke={i % 2 === 0 ? "#423D39" : "#7E7873"}
              strokeWidth="1.4"
            />
          ))}

          {/* Legs below skirt */}
          <rect x="88" y="264" width="7.5" height="26" fill="#F8D5BF" rx="3.5" />
          <rect x="104.5" y="264" width="7.5" height="26" fill="#F8D5BF" rx="3.5" />

          {/* Warm Brown Court Shoes */}
          <path
            d="M 82 288 Q 86 282 96 284 L 98 294 L 81 294 Z"
            fill="#5C3622"
          />
          <path
            d="M 118 288 Q 114 282 104 284 L 102 294 L 119 294 Z"
            fill="#5C3622"
          />
        </g>

        {/* ========================================================
            LAYER 2: BODY (Cardigan & Blouse)
            ======================================================== */}
        <motion.g
          id="teacher-body"
          variants={bodyVariants}
          animate={animKey}
          style={{ transformOrigin: "100px 172px" }}
        >
          {/* Neck */}
          <path
            d="M 94 84 L 94 102 L 106 102 L 106 84 Z"
            fill="url(#tchNeckShadow)"
          />

          {/* Inner Blouse Collar */}
          <path
            d="M 92 98 L 100 114 L 108 98 Z"
            fill="#DCD2C0"
          />
          <line x1="100" y1="100" x2="100" y2="114" stroke="#B8AB96" strokeWidth="1" />

          {/* Cream Cardigan - Main Torso */}
          <path
            d="M 76 98 Q 88 98 94 100 L 96 172 L 76 172 Q 74 135 76 98 Z"
            fill="url(#tchCardiganGrad)"
          />
          <path
            d="M 124 98 Q 112 98 106 100 L 104 172 L 124 172 Q 126 135 124 98 Z"
            fill="url(#tchCardiganGrad)"
          />

          {/* V-neck Trim & Buttons */}
          <path
            d="M 94 100 L 100 118 L 106 100"
            stroke="#DFD8C3"
            strokeWidth="3.2"
            fill="none"
          />
          <line x1="100" y1="118" x2="100" y2="172" stroke="#DFD8C3" strokeWidth="2.5" />
          <circle cx="100" cy="128" r="1.6" fill="#7E563D" />
          <circle cx="100" cy="144" r="1.6" fill="#7E563D" />
          <circle cx="100" cy="160" r="1.6" fill="#7E563D" />
        </motion.g>

        {/* ========================================================
            LAYER 3: LEFT ARM & BOOK PROP (Tucked Book / Open Book)
            ======================================================== */}
        <motion.g
          id="teacher-left-arm-group"
          variants={leftArmVariants}
          animate={animKey}
          style={{ transformOrigin: "78px 102px" }}
        >
          {/* Cardigan Sleeve */}
          <path
            d="M 78 98 Q 66 104 68 126 L 78 124 Q 80 110 78 98 Z"
            fill="url(#tchCardiganGrad)"
          />
          {/* Forearm */}
          <path
            d="M 68 126 L 72 158 Q 74 164 78 166 L 82 164 L 78 124 Z"
            fill="#F8D5BF"
          />
          <ellipse cx="78" cy="166" rx="4.5" ry="6" fill="#F8D5BF" />

          {/* Book Prop */}
          <g id="teacher-book-layer" transform="translate(60, 140)">
            {isExplaining ? (
              // Open Book during explaining
              <g>
                <rect x="0" y="0" width="38" height="26" rx="2.5" fill="url(#tchBookCover)" />
                <rect x="2" y="2" width="16" height="22" rx="1.5" fill="#F8F6EF" />
                <rect x="20" y="2" width="16" height="22" rx="1.5" fill="#F8F6EF" />
                <line x1="4" y1="6" x2="16" y2="6" stroke="#C8C0B2" strokeWidth="1" />
                <line x1="4" y1="10" x2="16" y2="10" stroke="#C8C0B2" strokeWidth="1" />
                <line x1="4" y1="14" x2="16" y2="14" stroke="#C8C0B2" strokeWidth="1" />
                <line x1="22" y1="6" x2="34" y2="6" stroke="#C8C0B2" strokeWidth="1" />
                <line x1="22" y1="10" x2="34" y2="10" stroke="#C8C0B2" strokeWidth="1" />
                <line x1="22" y1="14" x2="34" y2="14" stroke="#C8C0B2" strokeWidth="1" />
              </g>
            ) : (
              // Closed Book held against side
              <g>
                <rect x="2" y="0" width="24" height="32" rx="2.5" fill="url(#tchBookCover)" />
                <rect x="5" y="2" width="19" height="28" rx="1.5" fill="#F8F6EF" />
                <line x1="5" y1="2" x2="5" y2="30" stroke="#522718" strokeWidth="1.8" />
              </g>
            )}
          </g>
        </motion.g>

        {/* ========================================================
            LAYER 4: RIGHT ARM (Gesturing with Pointed Index Finger)
            ======================================================== */}
        <motion.g
          id="teacher-right-arm-group"
          variants={rightArmVariants}
          animate={animKey}
          style={{ transformOrigin: "122px 102px" }}
        >
          {/* Cardigan Sleeve */}
          <path
            d="M 122 98 Q 134 104 132 126 L 122 124 Q 120 110 122 98 Z"
            fill="url(#tchCardiganGrad)"
          />
          {/* Forearm angled up in explanation */}
          <path
            d="M 132 126 L 140 148 Q 142 152 138 156 L 130 152 L 122 124 Z"
            fill="#F8D5BF"
          />
          {/* Hand with poised index finger */}
          <ellipse cx="138" cy="150" rx="4.5" ry="5.5" fill="#F8D5BF" />
          <path
            d="M 137 148 L 140 134 Q 141 131 143 133 L 141 148 Z"
            fill="#F8D5BF"
          />
        </motion.g>

        {/* ========================================================
            LAYER 5, 6, 7: HEAD, CURLY HAIR, GLASSES & FACE
            ======================================================== */}
        <motion.g
          id="teacher-head-group"
          variants={headVariants}
          animate={animKey}
          style={{ transformOrigin: "100px 90px" }}
        >
          {/* Curly Hair Background Bulk */}
          <path
            d="M 64 56 Q 56 16 100 14 Q 144 16 136 56 Q 148 84 132 94 Q 100 96 68 94 Q 52 84 64 56 Z"
            fill="url(#tchHairGrad)"
          />
          {/* Voluminous Curly Ringlets */}
          <circle cx="66" cy="46" r="11" fill="#4D2E1B" />
          <circle cx="62" cy="62" r="12" fill="#3D2313" />
          <circle cx="64" cy="78" r="10" fill="#4D2E1B" />
          <circle cx="134" cy="46" r="11" fill="#4D2E1B" />
          <circle cx="138" cy="62" r="12" fill="#3D2313" />
          <circle cx="136" cy="78" r="10" fill="#4D2E1B" />

          {/* Head Base Skin */}
          <ellipse cx="100" cy="62" rx="28" ry="30" fill="url(#tchSkinGlow)" />
          <path
            d="M 76 66 Q 85 90 100 90 Q 115 90 124 66 Z"
            fill="url(#tchSkinGlow)"
          />

          {/* Cheeks Blush */}
          <circle cx="84" cy="68" r="6" fill="#F0A895" opacity="0.45" />
          <circle cx="116" cy="68" r="6" fill="#F0A895" opacity="0.45" />

          {/* Refined Nose */}
          <path
            d="M 98 60 Q 100 66 102 60"
            stroke="#D88F7C"
            strokeWidth="1.6"
            strokeLinecap="round"
            fill="none"
          />

          {/* Eyes (Blinking) */}
          <g
            id="teacher-eyes"
            style={{
              transformOrigin: "100px 56px",
              transform: blink ? "scaleY(0.1)" : "scaleY(1)",
              transition: "transform 0.15s ease-in-out",
            }}
          >
            {/* Left Eye */}
            <ellipse cx="87" cy="55" rx="7.5" ry="8.5" fill="#FFFFFF" />
            <circle cx="87" cy="55" r="5.6" fill="#5A351E" />
            <circle cx="87" cy="55" r="2.8" fill="#140C07" />
            <circle cx="89" cy="53" r="1.6" fill="#FFFFFF" />
            <path d="M 80 53 Q 87 48 94 53" stroke="#2B1B14" strokeWidth="1.5" fill="none" />

            {/* Right Eye */}
            <ellipse cx="113" cy="55" rx="7.5" ry="8.5" fill="#FFFFFF" />
            <circle cx="113" cy="55" r="5.6" fill="#5A351E" />
            <circle cx="113" cy="55" r="2.8" fill="#140C07" />
            <circle cx="115" cy="53" r="1.6" fill="#FFFFFF" />
            <path d="M 106 53 Q 113 48 120 53" stroke="#2B1B14" strokeWidth="1.5" fill="none" />
          </g>

          {/* Eyebrows */}
          <g id="teacher-eyebrows">
            {expression.brows === "raised" ? (
              <>
                <path d="M 80 43 Q 87 38 94 43" stroke="#4D2E1B" strokeWidth="2.4" strokeLinecap="round" fill="none" />
                <path d="M 106 43 Q 113 38 120 43" stroke="#4D2E1B" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              </>
            ) : expression.brows === "concerned" ? (
              <>
                <path d="M 81 46 Q 87 49 94 44" stroke="#4D2E1B" strokeWidth="2.4" strokeLinecap="round" fill="none" />
                <path d="M 106 44 Q 113 49 119 46" stroke="#4D2E1B" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              </>
            ) : (
              <>
                <path d="M 80 44 Q 87 40 94 44" stroke="#4D2E1B" strokeWidth="2.4" strokeLinecap="round" fill="none" />
                <path d="M 106 44 Q 113 40 120 44" stroke="#4D2E1B" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              </>
            )}
          </g>

          {/* Mouth */}
          <path
            d={expression.mouth}
            stroke="#BA5948"
            strokeWidth="2.4"
            strokeLinecap="round"
            fill={performance === "EXPLAINING" || performance === "SPEAKING" ? "#BA5948" : "none"}
          />

          {/* Round Glasses */}
          <g id="teacher-glasses">
            <circle cx="87" cy="55" r="10.8" stroke="#2B1B14" strokeWidth="2.4" fill="none" />
            <line x1="81" y1="48" x2="85" y2="44" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.4" />
            <circle cx="113" cy="55" r="10.8" stroke="#2B1B14" strokeWidth="2.4" fill="none" />
            <line x1="107" y1="48" x2="111" y2="44" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.4" />
            <path d="M 98 55 Q 100 52 102 55" stroke="#2B1B14" strokeWidth="2.4" fill="none" />
          </g>

          {/* Forehead Curls Framing */}
          <g id="teacher-curls-front">
            <path
              d="M 74 36 Q 84 24 94 34 Q 106 22 118 32 Q 126 26 128 36 Q 116 30 102 30 Q 86 30 74 36 Z"
              fill="#693F26"
            />
            <path d="M 82 30 Q 88 36 94 32" stroke="#4D2E1B" strokeWidth="2" fill="none" />
            <path d="M 106 30 Q 112 36 118 32" stroke="#4D2E1B" strokeWidth="2" fill="none" />
          </g>
        </motion.g>

        {/* ========================================================
            QUESTION MARK OVERLAYS (ASKING)
            ======================================================== */}
        {performance === "ASKING" && (
          <motion.text
            x="148"
            y="36"
            fontFamily="system-ui, -apple-system, sans-serif"
            fontSize="32"
            fontWeight="bold"
            fill="#3A63FF"
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
