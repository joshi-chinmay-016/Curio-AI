"use client";

import React, { useRef, useState, useEffect } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  useReducedMotion,
} from "framer-motion";
import { LucideIcon } from "lucide-react";

export interface FeynmanStep {
  number: string;
  mode: string;
  title: string;
  description: string;
  badge: string;
  badgeColor: string;
  icon: LucideIcon;
}

interface FeynmanLoop3DProps {
  steps: FeynmanStep[];
}

// ============================================================================
// 1. Ambient Depth Layer: Low-opacity floating geometric wireframes & gradients
// ============================================================================
function AmbientDepthLayer() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0"
    >
      {/* Soft gradient ambient halos */}
      <div className="absolute top-1/4 left-1/12 w-96 h-96 bg-cobalt/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/12 w-96 h-96 bg-gap-orange/5 rounded-full blur-3xl" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-navy/5 rounded-full blur-3xl" />

      {/* Floating isometric diamond wireframes */}
      <svg
        className="absolute top-12 left-10 w-24 h-24 text-navy/10 animate-pulse"
        style={{ animationDuration: "6s" }}
        viewBox="0 0 100 100"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
      >
        <polygon points="50,10 90,50 50,90 10,50" />
        <line x1="50" y1="10" x2="50" y2="90" strokeDasharray="3 3" />
        <line x1="10" y1="50" x2="90" y2="50" strokeDasharray="3 3" />
      </svg>

      <svg
        className="absolute bottom-16 right-16 w-32 h-32 text-cobalt/10 animate-pulse"
        style={{ animationDuration: "8s" }}
        viewBox="0 0 100 100"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
      >
        <polygon points="50,5 95,50 50,95 5,50" />
        <polygon points="50,25 75,50 50,75 25,50" strokeDasharray="2 2" />
      </svg>
    </div>
  );
}

// ============================================================================
// 2. Connecting Energy Line: Progressive SVG path with return loop arc
// ============================================================================
interface LoopConnectingPathProps {
  progress: any; // MotionValue<number>
  activeStep: number;
}

function LoopConnectingPath({ progress, activeStep }: LoopConnectingPathProps) {
  // Path across 5 cards and curving back over the top to close the loop
  // ViewBox: 0 0 1000 240
  // Card centers at Y ~ 150: X = 100, 300, 500, 700, 900
  // Return arc sweeps back over the top at Y ~ 35 from 900 to 100
  const forwardPath =
    "M 100 150 C 180 130, 220 170, 300 150 C 380 130, 420 170, 500 150 C 580 130, 620 170, 700 150 C 780 130, 820 170, 900 150";
  const returnArc =
    " C 960 150, 960 35, 900 35 L 100 35 C 40 35, 40 150, 100 150";
  const fullLoopPath = forwardPath + returnArc;

  const pathLength = useSpring(progress, { stiffness: 120, damping: 24 });
  const isLoopClosing = activeStep === 4;

  return (
    <div
      aria-hidden="true"
      className="hidden md:block absolute inset-0 pointer-events-none z-10 overflow-visible"
    >
      <svg
        className="w-full h-full"
        viewBox="0 0 1000 240"
        preserveAspectRatio="none"
        fill="none"
      >
        <defs>
          <linearGradient id="energyGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3A63FF" stopOpacity="0.8" />
            <stop offset="45%" stopColor="#0F2B4A" stopOpacity="0.7" />
            <stop offset="60%" stopColor="#FF6B1A" stopOpacity="0.9" />
            <stop offset="80%" stopColor="#3A63FF" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0F2B4A" stopOpacity="0.8" />
          </linearGradient>

          <filter id="energyGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Faint track background */}
        <path
          d={fullLoopPath}
          stroke="#C4CDD6"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          strokeOpacity="0.35"
        />

        {/* Soft atmospheric glow stroke */}
        <motion.path
          d={fullLoopPath}
          stroke="url(#energyGrad)"
          strokeWidth="5"
          strokeLinecap="round"
          filter="url(#energyGlow)"
          opacity={0.35}
          style={{ pathLength }}
        />

        {/* Crisp energetic foreground line */}
        <motion.path
          d={fullLoopPath}
          stroke="url(#energyGrad)"
          strokeWidth="2.2"
          strokeLinecap="round"
          style={{ pathLength }}
        />

        {/* Loop closing indicator tag above card 1-5 */}
        {isLoopClosing && (
          <g>
            <text
              x="500"
              y="22"
              fill="#0F2B4A"
              fontSize="10"
              fontFamily="var(--font-mono)"
              fontWeight="bold"
              letterSpacing="2"
              textAnchor="middle"
              opacity="0.75"
            >
              LOOP CLOSING: RETURN TO INQUIRY
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

// ============================================================================
// 3. Individual 3D Card with Mouse Tilt, Specular Reflection & Micro-Moments
// ============================================================================
interface Card3DProps {
  step: FeynmanStep;
  idx: number;
  isActive: boolean;
  activeStep: number;
  onSelect: () => void;
  reducedMotion: boolean | null;
}

function Card3D({
  step,
  idx,
  isActive,
  activeStep,
  onSelect,
  reducedMotion,
}: Card3DProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const Icon = step.icon;

  // Mouse tilt tracking
  const [isHovered, setIsHovered] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, px: 50, py: 50 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reducedMotion || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5; // -0.5 to 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    const px = ((e.clientX - rect.left) / rect.width) * 100;
    const py = ((e.clientY - rect.top) / rect.height) * 100;

    setMousePos({
      x: x * 14, // max 7 deg tilt
      y: -y * 14,
      px,
      py,
    });
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setMousePos({ x: 0, y: 0, px: 50, py: 50 });
  };

  // 3D Perspective Angles based on card index in row (center is idx 2)
  const perspectiveYAngle = (idx - 2) * 4; // -8deg, -4deg, 0deg, 4deg, 8deg
  const targetRotateY = isActive ? 0 : perspectiveYAngle;
  const targetTranslateZ = isActive ? 36 : -14;
  const targetScale = isActive ? 1.03 : 0.97;

  // Mode-based atmospheric ambient glow colors
  const modeGlowClass =
    step.mode === "TEACHER MODE"
      ? "from-gap-orange/20 to-transparent"
      : step.mode === "ANALYSIS"
      ? "from-navy/15 to-transparent"
      : "from-cobalt/20 to-transparent";

  // Check if card 1 should pulse on loop return (stage 5 active)
  const isCard1Rehighlighted = activeStep === 4 && idx === 0;

  return (
    <motion.div
      ref={cardRef}
      role="button"
      tabIndex={0}
      aria-label={`${step.number} ${step.title} (${step.mode})`}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      animate={
        reducedMotion
          ? { opacity: isActive ? 1 : 0.85, scale: isActive ? 1.02 : 1 }
          : {
              rotateY: isHovered ? mousePos.x : targetRotateY,
              rotateX: isHovered ? mousePos.y : 0,
              z: targetTranslateZ,
              scale: targetScale,
              opacity: isActive ? 1 : 0.82,
            }
      }
      transition={{
        type: "spring",
        stiffness: 280,
        damping: 24,
      }}
      style={{
        transformStyle: "preserve-3d",
      }}
      className={`relative p-5 rounded-[6px] cursor-pointer flex flex-col justify-between transition-colors duration-200 select-none ${
        isActive || isCard1Rehighlighted
          ? "bg-white border-2 border-navy shadow-[0_12px_30px_rgba(15,43,74,0.12),0_4px_0_0_#0F2B4A]"
          : "bg-white/85 border border-fog hover:border-navy/60 hover:bg-white shadow-sm"
      }`}
    >
      {/* Mode Atmospheric Glow Underlay */}
      {isActive && (
        <div
          aria-hidden="true"
          className={`absolute -inset-1 rounded-[8px] bg-gradient-to-b ${modeGlowClass} -z-10 blur-md pointer-events-none transition-opacity duration-300 opacity-80`}
        />
      )}

      {/* Dynamic Specular Glass Highlight on Hover */}
      {isHovered && !reducedMotion && (
        <div
          aria-hidden="true"
          className="absolute inset-0 rounded-[6px] pointer-events-none overflow-hidden z-20"
          style={{
            background: `radial-gradient(circle 120px at ${mousePos.px}% ${mousePos.py}%, rgba(255,255,255,0.7) 0%, transparent 80%)`,
          }}
        />
      )}

      {/* Micro-moment 02: Analysis Shimmer Scan Line */}
      {isActive && idx === 1 && (
        <motion.div
          aria-hidden="true"
          className="absolute inset-0 pointer-events-none rounded-[6px] overflow-hidden z-10"
        >
          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: "200%" }}
            transition={{
              repeat: Infinity,
              duration: 2.4,
              ease: "easeInOut",
              repeatDelay: 1,
            }}
            className="w-1/2 h-full bg-gradient-to-r from-transparent via-cobalt/10 to-transparent skew-x-12"
          />
        </motion.div>
      )}

      {/* Micro-moment 03: Gap Orange Pulse Edge */}
      {isActive && idx === 2 && (
        <div
          aria-hidden="true"
          className="absolute inset-0 rounded-[6px] border-2 border-gap-orange animate-gap-pulse pointer-events-none z-10"
        />
      )}

      {/* Card Header: Number & Badge */}
      <div className="z-10">
        <div className="flex items-center justify-between mb-3">
          <span
            className={`font-mono text-sm font-bold transition-colors ${
              isActive ? "text-navy" : "text-navy/40"
            }`}
          >
            {step.number}
          </span>

          {/* Badge with micro-moments */}
          <div className="relative">
            {isActive && idx === 0 && (
              <span
                aria-hidden="true"
                className="absolute -inset-0.5 rounded-[2px] bg-cobalt opacity-50 animate-ping"
              />
            )}
            <span
              className={`relative font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-[2px] inline-flex items-center gap-1 ${
                step.badgeColor
              } ${isActive && idx === 3 ? "animate-pulse" : ""}`}
            >
              {step.badge}
            </span>
          </div>
        </div>

        {/* Title */}
        <h3 className="font-heading text-base font-bold text-navy mb-2 tracking-tight">
          {step.title}
        </h3>

        {/* Description */}
        <p className="font-sans text-xs text-navy/75 leading-relaxed">
          {step.description}
        </p>
      </div>

      {/* Card Footer: Mode Label & Icon */}
      <div className="mt-4 pt-3 border-t border-fog/50 flex items-center justify-between font-mono text-[10px] text-navy/50 uppercase z-10">
        <span
          className={`transition-colors ${
            isActive ? "text-navy font-semibold" : "text-navy/50"
          }`}
        >
          {step.mode}
        </span>

        <div className="relative">
          <Icon
            className={`w-3.5 h-3.5 transition-transform duration-200 ${
              isActive
                ? "text-navy scale-110"
                : "text-navy/60 group-hover:scale-105"
            } ${isActive && idx === 1 ? "animate-spin" : ""}`}
            style={
              isActive && idx === 1 ? { animationDuration: "8s" } : undefined
            }
          />
        </div>
      </div>
    </motion.div>
  );
}

// ============================================================================
// 4. Main Component: FeynmanLoop3D
// ============================================================================
export function FeynmanLoop3D({ steps }: FeynmanLoop3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeStep, setActiveStep] = useState(0);
  const reducedMotion = useReducedMotion();

  // Scroll tracking across the sticky scroll track
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  // Smooth spring progress
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 140,
    damping: 26,
    restDelta: 0.001,
  });

  // Calculate active step dynamically based on scroll progress
  useEffect(() => {
    if (reducedMotion) return;

    const unsubscribe = scrollYProgress.on("change", (latest) => {
      // 5 stages mapped across 0.0 to 1.0:
      // 0: [0.00, 0.18)
      // 1: [0.18, 0.38)
      // 2: [0.38, 0.58)
      // 3: [0.58, 0.78)
      // 4: [0.78, 1.00]
      let currentIdx = 0;
      if (latest >= 0.78) {
        currentIdx = 4;
      } else if (latest >= 0.58) {
        currentIdx = 3;
      } else if (latest >= 0.38) {
        currentIdx = 2;
      } else if (latest >= 0.18) {
        currentIdx = 1;
      } else {
        currentIdx = 0;
      }
      setActiveStep(currentIdx);
    });

    return () => unsubscribe();
  }, [scrollYProgress, reducedMotion]);

  // Heading opacity & rise-in
  const headerOpacity = useTransform(scrollYProgress, [0, 0.08], [0.85, 1]);
  const headerY = useTransform(scrollYProgress, [0, 0.08], [10, 0]);

  return (
    <div
      ref={containerRef}
      className="relative w-full md:min-h-[260vh] border-t border-fog bg-white/40"
    >
      {/* Sticky Viewport Stage for Desktop 3D Pinning */}
      <div className="md:sticky md:top-0 md:h-screen w-full flex flex-col justify-center py-16 md:py-0 overflow-hidden">
        {/* Ambient Depth Background */}
        <AmbientDepthLayer />

        <div className="relative max-w-6xl w-full mx-auto px-6 z-10">
          {/* Section Header: Content Lock Maintained Byte-For-Byte */}
          <motion.div
            style={{
              opacity: reducedMotion ? 1 : headerOpacity,
              y: reducedMotion ? 0 : headerY,
            }}
            className="text-center max-w-2xl mx-auto mb-10 md:mb-14"
          >
            <span className="font-mono text-xs font-bold uppercase tracking-widest text-cobalt block mb-2">
              THE 5-STAGE FEYNMAN LOOP
            </span>
            <h2 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-4">
              How Curio Thinks With You
            </h2>
            <p className="font-sans text-base text-navy/70 leading-relaxed">
              Unlike standard chatbots that lecture you, Curio creates a dynamic two-way learning loop that systematically surfaces what you don't know.
            </p>
          </motion.div>

          {/* 3D Perspective Stage Container */}
          <div
            className="relative w-full"
            style={{
              perspective: reducedMotion ? "none" : "1200px",
            }}
          >
            {/* SVG Connecting Energy Line running between and behind cards */}
            <LoopConnectingPath
              progress={smoothProgress}
              activeStep={activeStep}
            />

            {/* 5-Card 3D Grid */}
            <div
              className="grid grid-cols-1 md:grid-cols-5 gap-4 relative z-10"
              style={{
                transformStyle: reducedMotion ? "flat" : "preserve-3d",
              }}
            >
              {steps.map((step, idx) => (
                <Card3D
                  key={step.number}
                  step={step}
                  idx={idx}
                  isActive={activeStep === idx}
                  activeStep={activeStep}
                  onSelect={() => setActiveStep(idx)}
                  reducedMotion={reducedMotion}
                />
              ))}
            </div>
          </div>

          {/* Interactive Stage Scrub Indicator Pills */}
          <div className="mt-8 md:mt-10 flex items-center justify-center gap-2">
            {steps.map((step, idx) => {
              const isPillActive = activeStep === idx;
              return (
                <button
                  key={step.number}
                  type="button"
                  onClick={() => setActiveStep(idx)}
                  aria-label={`Jump to stage ${step.number}: ${step.title}`}
                  className={`group relative flex items-center gap-1.5 px-2.5 py-1 rounded-[4px] font-mono text-[11px] font-bold transition-all duration-200 ${
                    isPillActive
                      ? "bg-navy text-white shadow-keycap"
                      : "bg-white/80 text-navy/50 hover:bg-white hover:text-navy border border-fog/60"
                  }`}
                >
                  <span>{step.number}</span>
                  <span
                    className={`hidden lg:inline text-[10px] uppercase tracking-wider ${
                      isPillActive ? "text-white/90" : "text-navy/40"
                    }`}
                  >
                    {step.badge.replace(" ✓", "")}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
