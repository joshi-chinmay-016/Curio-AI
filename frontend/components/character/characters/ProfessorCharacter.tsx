"use client";

import React, { useState, useEffect, useMemo } from "react";
import { motion, Variants, useAnimation } from "framer-motion";
import { PerformanceState, CharacterComponentProps } from "../types";

// ==========================================
// PROFESSOR ANIMATION VARIANTS (Economy of Motion = Authority)
// ==========================================

const headVariants: Variants = {
  IDLE: {
    rotate: 0,
    y: 0,
    // NO idle breathing bob — he is perfectly still and dignified
  },
  LISTENING: {
    rotate: -1.5,
    y: 0,
    transition: { type: "tween", duration: 0.6 },
  },
  LISTENING_ACTIVE: {
    rotate: -1.5,
    y: 0,
    transition: { type: "tween", duration: 0.6 },
  },
  LISTENING_IDLE: {
    rotate: -0.8,
    y: 0,
    transition: { type: "tween", duration: 0.6 },
  },
  EVALUATING: {
    rotate: 5,
    y: 8,
    transition: { type: "tween", duration: 0.5 },
  },
  MARKING: {
    rotate: 5,
    y: 8,
    transition: { type: "tween", duration: 0.5 },
  },
  SPEAKING: {
    rotate: [-0.5, 0.5, -0.5],
    y: [-0.5, -1.5, -0.5],
    transition: { duration: 1.6, repeat: Infinity, ease: "easeInOut" },
  },
  ASKING: {
    rotate: -1.8,
    y: -2,
    transition: { type: "spring", stiffness: 120, damping: 20 },
  },
  REACTING_STRICT: {
    rotate: [-1, -3.5, -1],
    transition: { duration: 0.5, ease: "easeInOut" },
  },
  REACTING_POSITIVE: {
    rotate: [0, 2.5, 0],
    y: [0, 2, 0],
    transition: { duration: 0.5, ease: "easeInOut" },
  },
  REACTING_GRUMPY: {
    rotate: [0, -2, -1, -2, 0],
    y: [0, 2, 1, 2, 3],
    transition: { duration: 0.8, ease: "easeInOut" },
  },
  ENTERING: {
    x: [80, 0],
    opacity: [0, 1],
    transition: { duration: 1.0, ease: [0.25, 0.1, 0.25, 1] },
  },
  EXITING: {
    x: [0, 100],
    opacity: [1, 0],
    transition: { duration: 0.8, ease: [0.55, 0, 1, 0.45] },
  },
};

const bodyVariants: Variants = {
  IDLE: {
    y: 0,
    rotate: 0,
    x: 0,
  },
  LISTENING: {
    rotate: -0.5,
    transition: { type: "tween", duration: 0.6 },
  },
  LISTENING_ACTIVE: {
    rotate: -0.5,
    transition: { type: "tween", duration: 0.6 },
  },
  EVALUATING: {
    rotate: 2,
    y: 3,
    transition: { type: "tween", duration: 0.5 },
  },
  MARKING: {
    rotate: 2,
    y: 3,
    transition: { type: "tween", duration: 0.5 },
  },
  ASKING: {
    x: 2,
    rotate: -1,
    transition: { type: "spring", stiffness: 140, damping: 18 },
  },
  REACTING_STRICT: {
    rotate: 0,
    y: 0,
  },
  REACTING_GRUMPY: {
    rotate: -4,
    y: 2,
    transition: { duration: 0.6 },
  },
};

export const ProfessorCharacter = ({
  performance,
  prefersReducedMotion = false,
  clipboardMark = "none",
  onExitComplete,
}: CharacterComponentProps) => {
  const [blink, setBlink] = useState(false);
  const grumpyControls = useAnimation();

  useEffect(() => {
    if (prefersReducedMotion) return;
    let timer: NodeJS.Timeout;

    const scheduleBlink = () => {
      const delay = 4000 + Math.random() * 2500;
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

  // Grumpy departure multi-step sequence
  useEffect(() => {
    if (performance === "REACTING_GRUMPY" && !prefersReducedMotion) {
      let isMounted = true;
      const runGrumpySeq = async () => {
        await grumpyControls.start({ rotate: -2, y: 2, transition: { duration: 0.4 } });
        if (!isMounted) return;

        await grumpyControls.start({ rotate: -8, transition: { duration: 0.6 } });
        if (!isMounted) return;

        await grumpyControls.start({
          x: 120,
          y: [2, -2, 2, -2, 6],
          opacity: [1, 1, 1, 0.8, 0],
          transition: { duration: 1.2, ease: [0.4, 0, 0.8, 0.4] },
        });
        if (!isMounted) return;

        onExitComplete?.();
      };

      runGrumpySeq();
      return () => {
        isMounted = false;
      };
    }
  }, [performance, prefersReducedMotion, grumpyControls, onExitComplete]);

  const expression = useMemo(() => {
    switch (performance) {
      case "REACTING_STRICT":
        return { brows: "stern", mouth: "strict" };
      case "EVALUATING":
      case "MARKING":
        return { brows: "evaluating", mouth: "neutral" };
      case "SPEAKING":
        return { brows: "neutral", mouth: "speaking" };
      case "ASKING":
        return { brows: "raised", mouth: "neutral" };
      case "REACTING_POSITIVE":
        return { brows: "neutral", mouth: "slight-smile" };
      case "REACTING_GRUMPY":
        return { brows: "stern", mouth: "frown" };
      case "IDLE":
      default:
        return { brows: "neutral", mouth: "neutral" };
    }
  }, [performance]);

  const animKey = prefersReducedMotion ? "IDLE" : performance;
  const isAsking = performance === "ASKING";
  const isEvaluating = performance === "EVALUATING" || performance === "MARKING";

  return (
    <div className="relative w-full h-full flex items-center justify-center select-none">
      <motion.div
        animate={grumpyControls}
        className="w-full h-full flex items-center justify-center"
      >
        <svg
          viewBox="0 0 200 320"
          width="100%"
          height="100%"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full object-contain filter drop-shadow-2xl"
        >
          <defs>
            {/* Skin Gradients */}
            <radialGradient id="prfSkinGlow" cx="50%" cy="38%" r="62%">
              <stop offset="0%" stopColor="#FFF2E4" />
              <stop offset="55%" stopColor="#ECC7A8" />
              <stop offset="100%" stopColor="#D3A27D" />
            </radialGradient>
            <linearGradient id="prfNeckShadow" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#C49068" />
              <stop offset="100%" stopColor="#ECC7A8" />
            </linearGradient>

            {/* Suit Navy Gradients */}
            <linearGradient id="prfSuitGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#142037" />
              <stop offset="25%" stopColor="#1C2B47" />
              <stop offset="75%" stopColor="#1C2B47" />
              <stop offset="100%" stopColor="#0F182B" />
            </linearGradient>

            {/* Tie Navy Gradient */}
            <linearGradient id="prfTieGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#243C6B" />
              <stop offset="100%" stopColor="#162747" />
            </linearGradient>

            {/* White Hair & Moustache Gradients */}
            <linearGradient id="prfHairGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#FFFFFF" />
              <stop offset="60%" stopColor="#F1F5F9" />
              <stop offset="100%" stopColor="#D3DCE6" />
            </linearGradient>
            <linearGradient id="prfMoustacheGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#FFFFFF" />
              <stop offset="100%" stopColor="#E2E8F0" />
            </linearGradient>

            {/* Clipboard Wood */}
            <linearGradient id="prfWoodGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#8C5C32" />
              <stop offset="100%" stopColor="#5E381A" />
            </linearGradient>
          </defs>

          {/* ========================================================
              LAYER 1: SUIT TROUSERS & SHOES (Lower body foundation)
              ======================================================== */}
          <g id="professor-lower-body">
            {/* Navy Suit Trousers */}
            <path
              d="M 80 186 L 77 282 L 95 282 L 97 186 Z"
              fill="#18243C"
            />
            <path
              d="M 103 186 L 105 282 L 123 282 L 120 186 Z"
              fill="#18243C"
            />
            <line x1="86" y1="190" x2="86" y2="280" stroke="#0F182B" strokeWidth="1.2" />
            <line x1="114" y1="190" x2="114" y2="280" stroke="#0F182B" strokeWidth="1.2" />

            {/* Formal Black Oxford Shoes */}
            <path
              d="M 72 284 Q 76 278 90 280 L 96 292 L 70 292 Z"
              fill="#0F172A"
            />
            <path
              d="M 128 284 Q 124 278 110 280 L 104 292 L 130 292 Z"
              fill="#0F172A"
            />
          </g>

          {/* ========================================================
              LAYER 2: BODY (Navy Tailored Suit Jacket, Shirt & Tie)
              ======================================================== */}
          <motion.g
            id="professor-body"
            variants={bodyVariants}
            animate={animKey}
            style={{ transformOrigin: "100px 186px" }}
          >
            {/* Neck */}
            <path
              d="M 94 82 L 94 100 L 106 100 L 106 82 Z"
              fill="url(#prfNeckShadow)"
            />

            {/* White Shirt Collar & Triangular Chest */}
            <polygon points="88,96 112,96 100,130" fill="#FFFFFF" />
            <polygon points="88,96 98,108 91,108" fill="#F1F5F9" />
            <polygon points="112,96 102,108 109,108" fill="#F1F5F9" />

            {/* Royal Navy Necktie */}
            <polygon points="97,105 103,105 104,111 96,111" fill="#1C3056" />
            <polygon points="97,111 103,111 104,142 100,148 96,142" fill="url(#prfTieGrad)" />

            {/* Suit Jacket Torso */}
            <path
              d="M 72 98 Q 86 98 94 100 L 96 186 L 72 186 Q 70 140 72 98 Z"
              fill="url(#prfSuitGrad)"
            />
            <path
              d="M 128 98 Q 114 98 106 100 L 104 186 L 128 186 Q 130 140 128 98 Z"
              fill="url(#prfSuitGrad)"
            />

            {/* Suit Lapels */}
            <path
              d="M 75 98 L 94 136 L 90 142 L 71 106 Z"
              fill="#142037"
            />
            <path
              d="M 125 98 L 106 136 L 110 142 L 129 106 Z"
              fill="#142037"
            />

            {/* Buttons */}
            <circle cx="100" cy="148" r="2" fill="#0A0F1D" stroke="#1E293B" strokeWidth="0.8" />
            <circle cx="100" cy="164" r="2" fill="#0A0F1D" stroke="#1E293B" strokeWidth="0.8" />

            {/* Flap Pockets */}
            <rect x="74" y="166" width="16" height="3" rx="1" fill="#121B2F" />
            <rect x="110" y="166" width="16" height="3" rx="1" fill="#121B2F" />
          </motion.g>

          {/* ========================================================
              LAYER 3: ARMS - FOLDED ARMS (Default Authoritative Pose)
              ======================================================== */}
          {!isAsking && (
            <motion.g
              id="professor-folded-arms"
              initial={{ opacity: 1 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <path
                d="M 72 104 Q 68 132 84 144 L 126 142 Q 134 136 130 114 L 120 116 Q 118 130 110 132 L 88 132 Q 80 126 80 108 Z"
                fill="url(#prfSuitGrad)"
              />
              <path
                d="M 128 104 Q 132 134 116 146 L 74 144 Q 66 138 70 118 L 80 120 Q 82 132 90 134 L 112 134 Q 120 128 120 108 Z"
                fill="url(#prfSuitGrad)"
              />
              <rect x="76" y="136" width="5.5" height="4" fill="#FFFFFF" rx="1" />
              <rect x="118.5" y="136" width="5.5" height="4" fill="#FFFFFF" rx="1" />
              <ellipse cx="80" cy="140" rx="4.5" ry="4" fill="#ECC7A8" />
              <ellipse cx="120" cy="140" rx="4.5" ry="4" fill="#ECC7A8" />
            </motion.g>
          )}

          {/* ========================================================
              LAYER 3b: ARMS - GESTURE ARM (Active during ASKING)
              ======================================================== */}
          {isAsking && (
            <motion.g
              id="professor-gesture-arm"
              initial={{ opacity: 0, rotate: 10 }}
              animate={{ opacity: 1, rotate: -15 }}
              exit={{ opacity: 0 }}
              transition={{ type: "spring", stiffness: 180, damping: 16 }}
              style={{ transformOrigin: "126px 104px" }}
            >
              <path
                d="M 126 102 Q 138 116 142 136 L 134 138 Q 128 122 122 106 Z"
                fill="url(#prfSuitGrad)"
              />
              <rect x="136" y="136" width="6" height="3" fill="#FFFFFF" rx="1" />
              <ellipse cx="142" cy="142" rx="4.5" ry="5.5" fill="#ECC7A8" />
              <line x1="140" y1="138" x2="144" y2="132" stroke="#ECC7A8" strokeWidth="2.2" strokeLinecap="round" />
            </motion.g>
          )}

          {/* ========================================================
              LAYER 4, 5, 6, 7, 8: HEAD, WHITE HAIR, GLASSES, MOUSTACHE & FACE
              ======================================================== */}
          <motion.g
            id="professor-head-group"
            variants={headVariants}
            animate={animKey}
            style={{ transformOrigin: "100px 88px" }}
          >
            {/* Back White Hair Volume */}
            <path
              d="M 64 54 Q 56 14 100 12 Q 144 14 136 54 Q 142 76 132 84 Q 100 86 68 84 Q 58 76 64 54 Z"
              fill="url(#prfHairGrad)"
            />

            {/* Head Base Skin */}
            <ellipse cx="100" cy="58" rx="28" ry="30" fill="url(#prfSkinGlow)" />
            <path
              d="M 76 62 Q 84 88 100 88 Q 116 88 124 62 Z"
              fill="url(#prfSkinGlow)"
            />

            {/* Forehead Wrinkle Lines */}
            <path d="M 88 38 Q 100 36 112 38" stroke="#D3A27D" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.6" />
            <path d="M 90 42 Q 100 40 110 42" stroke="#D3A27D" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.6" />

            {/* Broad Nose */}
            <path
              d="M 97 54 Q 100 62 103 54"
              stroke="#C49068"
              strokeWidth="2"
              strokeLinecap="round"
              fill="none"
            />
            <ellipse cx="100" cy="58" rx="4.8" ry="3.8" fill="#ECC7A8" />

            {/* Eyes behind spectacles (Blinking) */}
            <g
              id="professor-eyes"
              style={{
                transformOrigin: "100px 52px",
                transform: blink ? "scaleY(0.1)" : "scaleY(1)",
                transition: "transform 0.15s ease-in-out",
              }}
            >
              {/* Left Eye */}
              <ellipse cx="87" cy="52" rx="7" ry="7.5" fill="#FFFFFF" />
              <circle cx="87" cy="52" r="5.2" fill="#334155" />
              <circle cx="87" cy="52" r="2.8" fill="#0F172A" />
              <circle cx="89" cy="50.2" r="1.4" fill="#FFFFFF" />

              {/* Right Eye */}
              <ellipse cx="113" cy="52" rx="7" ry="7.5" fill="#FFFFFF" />
              <circle cx="113" cy="52" r="5.2" fill="#334155" />
              <circle cx="113" cy="52" r="2.8" fill="#0F172A" />
              <circle cx="115" cy="50.2" r="1.4" fill="#FFFFFF" />
            </g>

            {/* Bushy White Eyebrows */}
            <g id="professor-eyebrows">
              {expression.brows === "stern" ? (
                <>
                  <path d="M 78 43 Q 86 47 94 41" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" fill="none" />
                  <path d="M 106 41 Q 114 47 122 43" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" fill="none" />
                </>
              ) : expression.brows === "evaluating" ? (
                <>
                  <path d="M 79 44 L 94 42" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" />
                  <path d="M 106 42 L 121 44" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" />
                </>
              ) : expression.brows === "raised" ? (
                <>
                  <path d="M 78 39 Q 86 35 94 39" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" fill="none" />
                  <path d="M 106 39 Q 114 35 122 39" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" fill="none" />
                </>
              ) : (
                <>
                  <path d="M 78 42 Q 86 38 94 42" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" fill="none" />
                  <path d="M 106 42 Q 114 38 122 42" stroke="#FFFFFF" strokeWidth="3.6" strokeLinecap="round" fill="none" />
                </>
              )}
            </g>

            {/* Dark Spectacles Frames */}
            <g id="professor-glasses">
              {/* Left Lens */}
              <circle cx="87" cy="52" r="11" stroke="#1F2937" strokeWidth="2.6" fill="none" />
              <line x1="81" y1="46" x2="85" y2="42" stroke="#FFFFFF" strokeWidth="1.4" opacity="0.45" />
              {/* Right Lens */}
              <circle cx="113" cy="52" r="11" stroke="#1F2937" strokeWidth="2.6" fill="none" />
              <line x1="107" y1="46" x2="111" y2="42" stroke="#FFFFFF" strokeWidth="1.4" opacity="0.45" />
              {/* Bridge */}
              <path d="M 98 52 Q 100 49 102 52" stroke="#1F2937" strokeWidth="2.6" fill="none" />
              {/* Temples extending to ears */}
              <line x1="76" y1="52" x2="70" y2="52" stroke="#1F2937" strokeWidth="2.2" />
              <line x1="124" y1="52" x2="130" y2="52" stroke="#1F2937" strokeWidth="2.2" />
            </g>

            {/* Full White Beard framing Jaw */}
            <path
              d="M 72 64 Q 68 90 100 96 Q 132 90 128 64 Q 122 76 100 80 Q 78 76 72 64 Z"
              fill="url(#prfHairGrad)"
            />

            {/* Prominent White Moustache (DEFINING FEATURE) */}
            <g id="professor-moustache">
              <path
                d="M 100 66 Q 88 63 76 66 Q 68 70 71 78 Q 83 78 94 73 Q 98 71 100 66 Z"
                fill="url(#prfMoustacheGrad)"
                stroke="#E2E8F0"
                strokeWidth="1"
              />
              <path
                d="M 100 66 Q 112 63 124 66 Q 132 70 129 78 Q 117 78 106 73 Q 102 71 100 66 Z"
                fill="url(#prfMoustacheGrad)"
                stroke="#E2E8F0"
                strokeWidth="1"
              />
              <circle cx="100" cy="66" r="3" fill="#FFFFFF" />
            </g>

            {/* White Swept Hair Crest on Top */}
            <g id="professor-hair-top">
              <path
                d="M 72 44 Q 66 20 92 16 Q 110 12 126 18 Q 134 26 128 44 Q 120 22 102 20 Q 84 20 72 44 Z"
                fill="url(#prfHairGrad)"
              />
              <path d="M 82 22 Q 92 16 102 18" stroke="#CBD5E1" strokeWidth="1.8" fill="none" />
              <path d="M 104 16 Q 114 16 122 24" stroke="#CBD5E1" strokeWidth="1.8" fill="none" />
            </g>
          </motion.g>

          {/* ========================================================
              LAYER 9: CLIPBOARD PROP (Appears in EVALUATING / MARKING)
              ======================================================== */}
          {isEvaluating && (
            <motion.g
              id="professor-clipboard-layer"
              initial={{ opacity: 0, y: 15, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 15, scale: 0.9 }}
              transition={{ type: "spring", stiffness: 200, damping: 18 }}
              transform="translate(64, 146)"
            >
              {/* Wood Clipboard Board */}
              <rect
                x="0"
                y="10"
                width="72"
                height="86"
                rx="5"
                fill="url(#prfWoodGrad)"
                stroke="#3D2612"
                strokeWidth="2.4"
              />
              {/* Brass / Silver Clip at top */}
              <rect x="22" y="4" width="28" height="14" rx="3.5" fill="#94A3B8" stroke="#475569" strokeWidth="1.2" />
              <circle cx="36" cy="8" r="2.4" fill="#334155" />

              {/* Assessment Paper */}
              <rect x="7" y="16" width="58" height="74" rx="2.5" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1.2" />

              {/* Lines on paper */}
              {[28, 40, 52, 64, 76].map((y) => (
                <line key={y} x1="14" y1={y} x2="58" y2={y} stroke="#E2E8F0" strokeWidth="1.5" />
              ))}

              {/* Assessment Mark: Checkmark if positive, Cross if negative */}
              {clipboardMark === "check" && (
                <motion.path
                  d="M 20 54 L 32 66 L 52 40"
                  stroke="#3A63FF"
                  strokeWidth="3.6"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              )}

              {clipboardMark === "cross" && (
                <g>
                  <motion.line
                    x1="24"
                    y1="44"
                    x2="48"
                    y2="66"
                    stroke="#FF6B1A"
                    strokeWidth="3.6"
                    strokeLinecap="round"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.3 }}
                  />
                  <motion.line
                    x1="48"
                    y1="44"
                    x2="24"
                    y2="66"
                    stroke="#FF6B1A"
                    strokeWidth="3.6"
                    strokeLinecap="round"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.3, delay: 0.15 }}
                  />
                </g>
              )}
            </motion.g>
          )}
        </svg>
      </motion.div>
    </div>
  );
};
