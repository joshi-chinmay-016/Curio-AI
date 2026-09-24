"use client";

import React, { useRef, useState } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  useReducedMotion,
} from "framer-motion";

// ============================================================================
// 1. Ambient Background: Blueprint Dot Grid, Drifting Wireframes & Geometry
// ============================================================================
function AmbientBackground() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0"
    >
      {/* Subtle Technical Dot Matrix Blueprint Grid */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage: "radial-gradient(#0F2B4A 1.2px, transparent 1.2px)",
          backgroundSize: "28px 28px",
        }}
      />

      {/* Atmospheric Radial Halos */}
      <div className="absolute top-1/4 -left-20 w-[420px] h-[420px] bg-fog/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 -right-20 w-[500px] h-[500px] bg-cobalt/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-navy/5 rounded-full blur-3xl pointer-events-none" />

      {/* LEFT FLANK: Drifting Dissolving Wireframe Elements (The Illusion / Decay) */}
      <motion.div
        animate={{ y: [0, -14, 0], rotate: [0, -2, 0] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        className="hidden lg:block absolute top-28 left-8 w-28 h-36 border border-dashed border-navy/20 rounded-[6px] bg-ice/20 p-3 opacity-60"
      >
        <div className="w-12 h-1.5 bg-navy/15 rounded-full mb-2" />
        <div className="w-20 h-1 bg-navy/10 rounded-full mb-1.5" />
        <div className="w-16 h-1 bg-navy/10 rounded-full mb-1.5" />
        <div className="w-14 h-1 bg-navy/10 rounded-full mb-4" />
        {/* Fading trail */}
        <div className="w-8 h-1 bg-navy/5 rounded-full" />
      </motion.div>

      <motion.div
        animate={{ y: [0, 12, 0], rotate: [0, 3, 0] }}
        transition={{ duration: 8.5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        className="hidden lg:block absolute bottom-24 left-14 w-20 h-24 border border-fog/40 rounded-[4px] bg-white/40 p-2.5 opacity-40"
      >
        <div className="w-8 h-1 bg-navy/20 rounded-full mb-2" />
        <div className="w-12 h-1 bg-navy/10 rounded-full mb-1" />
        <div className="w-10 h-1 bg-navy/10 rounded-full" />
      </motion.div>

      {/* Floating Desaturated Cube Wireframe */}
      <svg
        className="hidden md:block absolute top-1/3 left-4 w-20 h-20 text-navy/15"
        viewBox="0 0 100 100"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
      >
        <polygon points="50,15 85,35 85,75 50,95 15,75 15,35" strokeDasharray="3 3" />
        <line x1="50" y1="15" x2="50" y2="55" strokeDasharray="3 3" />
        <line x1="85" y1="35" x2="50" y2="55" strokeDasharray="3 3" />
        <line x1="15" y1="35" x2="50" y2="55" strokeDasharray="3 3" />
      </svg>

      {/* RIGHT FLANK: Solid 3D Isometric Prisms & Orbitals (Curio / Active Mastery) */}
      <motion.div
        animate={{ y: [0, -16, 0], rotateZ: [0, 5, 0] }}
        transition={{ duration: 6.5, repeat: Infinity, ease: "easeInOut" }}
        className="hidden lg:block absolute top-24 right-10 w-24 h-24"
      >
        <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible">
          {/* Orbital Ring */}
          <ellipse
            cx="50"
            cy="50"
            rx="45"
            ry="18"
            fill="none"
            stroke="#3A63FF"
            strokeWidth="1.5"
            strokeOpacity="0.4"
            transform="rotate(-25 50 50)"
          />
          {/* Traveling Node on Orbital */}
          <circle cx="20" cy="42" r="3.5" fill="#3A63FF" className="animate-pulse" />

          {/* Floating Solid Isometric Mini Cube */}
          <g transform="translate(36, 32)">
            <polygon points="14,0 28,8 14,16 0,8" fill="#E8EEF3" stroke="#0F2B4A" strokeWidth="1" />
            <polygon points="0,8 14,16 14,30 0,22" fill="#3A63FF" stroke="#0F2B4A" strokeWidth="1" />
            <polygon points="14,16 28,8 28,22 14,30" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="1" />
          </g>
        </svg>
      </motion.div>

      <motion.div
        animate={{ y: [0, 14, 0], rotateZ: [0, -4, 0] }}
        transition={{ duration: 7.8, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
        className="hidden lg:block absolute bottom-20 right-14 w-28 h-28"
      >
        <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible">
          {/* Layered Hexagonal Badge outline */}
          <polygon
            points="50,10 88,32 88,76 50,98 12,76 12,32"
            fill="none"
            stroke="#0F2B4A"
            strokeWidth="1.2"
            strokeOpacity="0.15"
          />
          {/* Inner Orange Accent Diamond */}
          <polygon
            points="50,30 70,50 50,70 30,50"
            fill="#FF6B1A"
            fillOpacity="0.12"
            stroke="#FF6B1A"
            strokeWidth="1.2"
            strokeOpacity="0.5"
          />
        </svg>
      </motion.div>
    </div>
  );
}

// ============================================================================
// 2. Decorative Multi-Stage Forgetting Visualizer (Left Card Bottom)
// ============================================================================
function ForgettingVisualizer() {
  return (
    <div aria-hidden="true" className="mt-8 pt-4 border-t border-fog/50 relative select-none">
      <div className="relative w-full h-28 overflow-visible">
        <svg
          className="w-full h-full overflow-visible"
          viewBox="0 0 340 100"
          preserveAspectRatio="none"
          fill="none"
        >
          <defs>
            {/* Shaded Decay Area Gradient */}
            <linearGradient id="decayArea" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#0F2B4A" stopOpacity="0.14" />
              <stop offset="60%" stopColor="#C4CDD6" stopOpacity="0.05" />
              <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
            </linearGradient>

            {/* Glowing Decay Curve Stroke */}
            <linearGradient id="decayStroke" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#0F2B4A" stopOpacity="0.75" />
              <stop offset="45%" stopColor="#0F2B4A" stopOpacity="0.5" />
              <stop offset="85%" stopColor="#C4CDD6" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#C4CDD6" stopOpacity="0.15" />
            </linearGradient>
          </defs>

          {/* Background Retention Grid Lines */}
          <line x1="10" y1="20" x2="330" y2="20" stroke="#C4CDD6" strokeWidth="0.8" strokeDasharray="3 4" strokeOpacity="0.4" />
          <line x1="10" y1="50" x2="330" y2="50" stroke="#C4CDD6" strokeWidth="0.8" strokeDasharray="3 4" strokeOpacity="0.4" />
          <line x1="10" y1="80" x2="330" y2="80" stroke="#C4CDD6" strokeWidth="0.8" strokeDasharray="3 4" strokeOpacity="0.4" />

          {/* Shaded Area Under Primary Curve */}
          <path
            d="M 10 18 C 75 22, 160 62, 330 84 L 330 95 L 10 95 Z"
            fill="url(#decayArea)"
          />

          {/* Secondary Faint Memory Ghost Curve */}
          <path
            d="M 10 32 C 80 40, 180 72, 330 88"
            stroke="#0F2B4A"
            strokeWidth="1.2"
            strokeDasharray="4 4"
            strokeOpacity="0.25"
          />

          {/* Primary Steep Forgetting Curve */}
          <path
            d="M 10 18 C 75 22, 160 62, 330 84"
            stroke="url(#decayStroke)"
            strokeWidth="2.4"
            strokeLinecap="round"
          />

          {/* Memory Nodes Sliding Downward */}
          <circle cx="16" cy="18.5" r="4" fill="#0F2B4A" />
          <circle cx="16" cy="18.5" r="7" fill="#0F2B4A" fillOpacity="0.15" className="animate-ping" style={{ animationDuration: "3s" }} />

          <circle cx="85" cy="27" r="3.5" fill="#0F2B4A" fillOpacity="0.75" />
          <circle cx="165" cy="54" r="3" fill="#0F2B4A" fillOpacity="0.5" />
          <circle cx="250" cy="74" r="2.5" fill="#0F2B4A" fillOpacity="0.35" />
          <circle cx="325" cy="83.5" r="2" fill="#C4CDD6" fillOpacity="0.6" />
        </svg>

        {/* Fading Memory Dust Dissolve Particles */}
        <motion.div
          animate={{ y: [0, -18], opacity: [0.6, 0] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeOut" }}
          className="absolute top-4 left-1/3 w-1.5 h-1.5 rounded-full bg-navy/30 pointer-events-none"
        />
        <motion.div
          animate={{ y: [0, -22], opacity: [0.5, 0] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeOut", delay: 0.8 }}
          className="absolute top-10 left-1/2 w-1.5 h-1.5 rounded-full bg-navy/20 pointer-events-none"
        />
        <motion.div
          animate={{ y: [0, -16], opacity: [0.4, 0] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut", delay: 1.4 }}
          className="absolute top-14 left-3/4 w-1 h-1 rounded-full bg-navy/15 pointer-events-none"
        />
      </div>
    </div>
  );
}

// ============================================================================
// 3. Decorative 3D Isometric Gap Laboratory Platform (Right Card Bottom)
// ============================================================================
function IsometricGapLaboratory() {
  return (
    <div aria-hidden="true" className="mt-8 pt-4 border-t border-navy/10 relative select-none">
      <div className="relative w-full h-28 flex items-center justify-between">
        {/* Left Side: Faint Blueprint Connection Pipeline */}
        <div className="flex flex-col gap-1.5 opacity-60">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cobalt inline-block animate-pulse" />
            <div className="w-16 h-1 bg-cobalt/30 rounded-full" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-gap-orange inline-block" />
            <div className="w-24 h-1 bg-gap-orange/30 rounded-full" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-navy/40 inline-block" />
            <div className="w-20 h-1 bg-navy/20 rounded-full" />
          </div>
        </div>

        {/* Right Side: Rich 3D Isometric Cube Platform */}
        <div className="relative w-48 h-28">
          <svg
            className="w-full h-full overflow-visible"
            viewBox="0 0 180 110"
            fill="none"
          >
            {/* Base Isometric Plate Grid */}
            <polygon
              points="90,15 170,55 90,95 10,55"
              fill="#E8EEF3"
              fillOpacity="0.45"
              stroke="#0F2B4A"
              strokeWidth="1"
              strokeDasharray="3 3"
              strokeOpacity="0.35"
            />

            {/* Platform Grid Coordinate Crosses */}
            <circle cx="90" cy="55" r="1.5" fill="#3A63FF" fillOpacity="0.6" />
            <circle cx="50" cy="35" r="1.5" fill="#3A63FF" fillOpacity="0.6" />
            <circle cx="130" cy="35" r="1.5" fill="#3A63FF" fillOpacity="0.6" />
            <circle cx="50" cy="75" r="1.5" fill="#3A63FF" fillOpacity="0.6" />
            <circle cx="130" cy="75" r="1.5" fill="#3A63FF" fillOpacity="0.6" />

            {/* Cube 1: Left Base (Chalk / Ice) */}
            <g transform="translate(30, 48)">
              <polygon points="14,0 28,8 14,16 0,8" fill="#FFFFFF" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="0,8 14,16 14,30 0,22" fill="#E8EEF3" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="14,16 28,8 28,22 14,30" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="0.9" />
            </g>

            {/* Cube 2: Center Base Front (Navy) */}
            <g transform="translate(62, 58)">
              <polygon points="14,0 28,8 14,16 0,8" fill="#E8EEF3" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="0,8 14,16 14,30 0,22" fill="#3A63FF" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="14,16 28,8 28,22 14,30" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="0.9" />
            </g>

            {/* Cube 3: Right Base (Navy) */}
            <g transform="translate(94, 48)">
              <polygon points="14,0 28,8 14,16 0,8" fill="#FFFFFF" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="0,8 14,16 14,30 0,22" fill="#C4CDD6" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="14,16 28,8 28,22 14,30" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="0.9" />
            </g>

            {/* Cube 4: Far Right Wing (Cobalt) */}
            <g transform="translate(122, 38)">
              <polygon points="14,0 28,8 14,16 0,8" fill="#3A63FF" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="0,8 14,16 14,30 0,22" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="14,16 28,8 28,22 14,30" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="0.9" />
            </g>

            {/* Cube 5: Tier 2 Stacked Left (Ice) */}
            <g transform="translate(46, 28)">
              <polygon points="14,0 28,8 14,16 0,8" fill="#FFFFFF" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="0,8 14,16 14,30 0,22" fill="#E8EEF3" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="14,16 28,8 28,22 14,30" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="0.9" />
            </g>

            {/* Cube 6: Tier 2 Stacked Center (Cobalt) */}
            <g transform="translate(78, 36)">
              <polygon points="14,0 28,8 14,16 0,8" fill="#E8EEF3" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="0,8 14,16 14,30 0,22" fill="#3A63FF" stroke="#0F2B4A" strokeWidth="0.9" />
              <polygon points="14,16 28,8 28,22 14,30" fill="#0F2B4A" stroke="#0F2B4A" strokeWidth="0.9" />
            </g>

            {/* CUBE 7: THE ELEVATED "GAP IDENTIFIED" VOXEL (Vibrant Orange & Pulsing!) */}
            <g transform="translate(86, 12)">
              {/* Radar Detection Beam */}
              <line x1="14" y1="-14" x2="14" y2="40" stroke="#FF6B1A" strokeWidth="1.2" strokeDasharray="3 3" strokeOpacity="0.8" />

              {/* Pulsing Orange Target Aura */}
              <circle cx="14" cy="14" r="22" fill="#FF6B1A" fillOpacity="0.22" className="animate-pulse" />

              {/* The Orange Gap Voxel */}
              <polygon points="14,0 28,8 14,16 0,8" fill="#FF8C42" stroke="#0F2B4A" strokeWidth="1.2" />
              <polygon points="0,8 14,16 14,30 0,22" fill="#FF6B1A" stroke="#0F2B4A" strokeWidth="1.2" />
              <polygon points="14,16 28,8 28,22 14,30" fill="#D94E00" stroke="#0F2B4A" strokeWidth="1.2" />
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 4. Main Component: LearningParadox3D
// ============================================================================
export function LearningParadox3D() {
  const sectionRef = useRef<HTMLElement>(null);
  const leftCardRef = useRef<HTMLDivElement>(null);
  const rightCardRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

  // Scroll tracking across section
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  });

  const smoothScroll = useSpring(scrollYProgress, {
    stiffness: 120,
    damping: 24,
    restDelta: 0.001,
  });

  // 1. Heading "Illusion" Mirage Parallax Layer Values
  const mirageDist = useTransform(smoothScroll, [0.1, 0.45], [5, 0]);
  const mirageOpacity = useTransform(smoothScroll, [0.1, 0.45], [0.4, 0]);
  const mirageBlur = useTransform(smoothScroll, [0.1, 0.45], [1.5, 0]);

  // 2. Traditional Card Decay Transformations (Left Card)
  const leftCardZ = useTransform(smoothScroll, [0.1, 0.55], [-70, -18]);
  const leftCardRotateY = useTransform(smoothScroll, [0.1, 0.55], [8, 4.5]);
  const leftBulletsOpacity = useTransform(smoothScroll, [0.4, 0.8], [0.95, 0.65]);
  const forgetBlur = useTransform(smoothScroll, [0.45, 0.8], [0, 1.5]);
  const forgetOpacity = useTransform(smoothScroll, [0.45, 0.8], [1, 0.5]);

  // 3. Curio Card Solid 3D Transformations (Right Card)
  const rightCardZ = useTransform(smoothScroll, [0.1, 0.55], [35, 28]);
  const rightCardScale = useTransform(smoothScroll, [0.1, 0.55], [0.98, 1.025]);
  const rightCardRotateY = useTransform(smoothScroll, [0.1, 0.55], [-7, -2]);

  // Mouse Hover Tilt State
  const [leftTilt, setLeftTilt] = useState({ x: 0, y: 0, px: 50, py: 50, isHovered: false });
  const [rightTilt, setRightTilt] = useState({ x: 0, y: 0, px: 50, py: 50, isHovered: false });

  const handleLeftMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reducedMotion || !leftCardRef.current) return;
    const rect = leftCardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setLeftTilt({
      x: x * 14,
      y: -y * 14,
      px: ((e.clientX - rect.left) / rect.width) * 100,
      py: ((e.clientY - rect.top) / rect.height) * 100,
      isHovered: true,
    });
  };

  const handleRightMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reducedMotion || !rightCardRef.current) return;
    const rect = rightCardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setRightTilt({
      x: x * 14,
      y: -y * 14,
      px: ((e.clientX - rect.left) / rect.width) * 100,
      py: ((e.clientY - rect.top) / rect.height) * 100,
      isHovered: true,
    });
  };

  return (
    <section
      ref={sectionRef}
      id="how-it-works"
      className="relative py-24 md:py-32 border-t border-fog bg-white overflow-hidden select-none"
    >
      {/* Ambient Blueprint Grid & 3D Geometry */}
      <AmbientBackground />

      <div className="relative max-w-6xl mx-auto px-6 z-10">
        {/* Section Header: Content Lock Maintained Byte-For-Byte */}
        <motion.div
          initial={reducedMotion ? {} : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="text-center max-w-xl mx-auto mb-16 md:mb-20"
        >
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-navy/50 block mb-2">
            THE LEARNING PARADOX
          </span>

          <h2 className="font-heading text-3xl md:text-4xl font-extrabold text-navy tracking-tight mb-4">
            Passive Learning Is An{" "}
            {/* The "Illusion" Word with Ghost Mirage Parallax */}
            <span className="relative inline-block whitespace-nowrap">
              <span className="relative z-10">Illusion</span>

              {!reducedMotion && (
                <>
                  <motion.span
                    aria-hidden="true"
                    style={{
                      x: useTransform(mirageDist, (d) => -d),
                      y: useTransform(mirageDist, (d) => -d * 0.5),
                      opacity: mirageOpacity,
                      filter: useTransform(mirageBlur, (b) => `blur(${b}px)`),
                    }}
                    className="absolute inset-0 text-cobalt pointer-events-none select-none -z-10"
                  >
                    Illusion
                  </motion.span>
                  <motion.span
                    aria-hidden="true"
                    style={{
                      x: useTransform(mirageDist, (d) => d * 1.3),
                      y: useTransform(mirageDist, (d) => d * 0.4),
                      opacity: mirageOpacity,
                      filter: useTransform(mirageBlur, (b) => `blur(${b * 1.2}px)`),
                    }}
                    className="absolute inset-0 text-gap-orange pointer-events-none select-none -z-10"
                  >
                    Illusion
                  </motion.span>
                </>
              )}
            </span>
          </h2>

          <p className="font-sans text-base text-navy/70 leading-relaxed">
            When you re-read notes or watch lectures, your brain confuses familiarity with true mastery.
          </p>
        </motion.div>

        {/* 3D Perspective Grid */}
        <div
          className="relative grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12 max-w-4xl mx-auto items-stretch"
          style={{ perspective: reducedMotion ? "none" : "1200px" }}
        >
          {/* Subtle Center Divider Line that shifts from Gray to Blue */}
          <motion.div
            aria-hidden="true"
            className="hidden md:block absolute left-1/2 top-6 bottom-6 w-px -translate-x-1/2 pointer-events-none z-0"
            style={{
              background: "linear-gradient(to bottom, #C4CDD6 0%, #3A63FF 50%, #C4CDD6 100%)",
              opacity: useTransform(smoothScroll, [0.2, 0.7], [0.25, 0.7]),
            }}
          />

          {/* ================================================================
              LEFT CARD: TRADITIONAL APPROACH (Decay / Ghost Layers)
             ================================================================ */}
          <div className="relative group" style={{ transformStyle: "preserve-3d" }}>
            {/* Drifting Ghost "Paper" Layers Stacked Behind */}
            {!reducedMotion && (
              <>
                <motion.div
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] border border-fog/50 bg-ice/40 -z-10 pointer-events-none shadow-sm"
                  style={{
                    x: leftTilt.isHovered ? -12 : -6,
                    y: leftTilt.isHovered ? 10 : 5,
                    rotateZ: leftTilt.isHovered ? -3 : -1.5,
                    opacity: 0.6,
                  }}
                />
                <motion.div
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] border border-fog/30 bg-ice/25 -z-20 pointer-events-none shadow-sm"
                  style={{
                    x: leftTilt.isHovered ? -22 : -11,
                    y: leftTilt.isHovered ? 18 : 9,
                    rotateZ: leftTilt.isHovered ? -5 : -2.8,
                    opacity: 0.35,
                  }}
                />
              </>
            )}

            <motion.div
              ref={leftCardRef}
              onMouseMove={handleLeftMouseMove}
              onMouseEnter={() => setLeftTilt((prev) => ({ ...prev, isHovered: true }))}
              onMouseLeave={() => setLeftTilt({ x: 0, y: 0, px: 50, py: 50, isHovered: false })}
              animate={
                reducedMotion
                  ? {}
                  : {
                    rotateY: leftTilt.isHovered ? leftTilt.x : 4.5,
                    rotateX: leftTilt.isHovered ? leftTilt.y : 0,
                    opacity: leftTilt.isHovered ? 0.92 : 1,
                  }
              }
              style={{
                z: reducedMotion ? 0 : leftCardZ,
                rotateY: reducedMotion ? 0 : leftCardRotateY,
                transformStyle: "preserve-3d",
              }}
              transition={{ type: "spring", stiffness: 260, damping: 24 }}
              className="relative h-full bg-ice/50 border border-fog rounded-[8px] p-8 flex flex-col justify-between overflow-hidden shadow-sm transition-colors duration-200"
            >
              {/* Specular Highlight on Hover */}
              {leftTilt.isHovered && !reducedMotion && (
                <div
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] pointer-events-none z-20"
                  style={{
                    background: `radial-gradient(circle 160px at ${leftTilt.px}% ${leftTilt.py}%, rgba(255,255,255,0.7) 0%, transparent 80%)`,
                  }}
                />
              )}

              <div>
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-navy/40 block mb-3">
                  TRADITIONAL APPROACH
                </span>

                <h3 className="font-heading text-xl font-bold text-navy mb-4">
                  Read → Memorize →{" "}
                  <motion.span
                    className="inline-block"
                    style={
                      reducedMotion
                        ? {}
                        : {
                          filter: useTransform(forgetBlur, (b) => `blur(${b}px)`),
                          opacity: forgetOpacity,
                        }
                    }
                  >
                    Forget
                  </motion.span>
                </h3>

                <motion.ul
                  style={reducedMotion ? {} : { opacity: leftBulletsOpacity }}
                  className="space-y-3.5 font-sans text-sm text-navy/75"
                >
                  <li className="flex items-start gap-2.5">
                    <span className="text-navy/40 font-bold inline-block select-none">✗</span>
                    <span>Passive consumption creates false confidence.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <span className="text-navy/40 font-bold inline-block select-none">✗</span>
                    <span>Boundary conditions and edge cases remain hidden until exams or production incidents.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <span className="text-navy/40 font-bold inline-block select-none">✗</span>
                    <span>Generic AI chat gives you answers without challenging your assumptions.</span>
                  </li>
                </motion.ul>
              </div>

              {/* Decorative Text-Free Forgetting Visualizer */}
              <ForgettingVisualizer />
            </motion.div>
          </div>

          {/* ================================================================
              RIGHT CARD: CURIO FEYNMAN SYSTEM (Solid Extrusion / Alive)
             ================================================================ */}
          <div className="relative group" style={{ transformStyle: "preserve-3d" }}>
            {/* Real 3D Layered Extrusion Stack Behind the Card */}
            {!reducedMotion && (
              <>
                {/* Extrusion Layer 3 (deepest navy) */}
                <motion.div
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] bg-navy pointer-events-none -z-30 shadow-xl"
                  animate={{
                    x: rightTilt.isHovered ? 12 : 6,
                    y: rightTilt.isHovered ? 12 : 6,
                  }}
                  transition={{ type: "spring", stiffness: 280, damping: 22 }}
                />
                {/* Extrusion Layer 2 (mid navy) */}
                <motion.div
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] bg-navy/90 pointer-events-none -z-20"
                  animate={{
                    x: rightTilt.isHovered ? 8 : 4,
                    y: rightTilt.isHovered ? 8 : 4,
                  }}
                  transition={{ type: "spring", stiffness: 280, damping: 22 }}
                />
                {/* Extrusion Layer 1 (close navy) */}
                <motion.div
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] bg-navy/80 pointer-events-none -z-10"
                  animate={{
                    x: rightTilt.isHovered ? 4 : 2,
                    y: rightTilt.isHovered ? 4 : 2,
                  }}
                  transition={{ type: "spring", stiffness: 280, damping: 22 }}
                />
              </>
            )}

            <motion.div
              ref={rightCardRef}
              onMouseMove={handleRightMouseMove}
              onMouseEnter={() => setRightTilt((prev) => ({ ...prev, isHovered: true }))}
              onMouseLeave={() => setRightTilt({ x: 0, y: 0, px: 50, py: 50, isHovered: false })}
              animate={
                reducedMotion
                  ? {}
                  : {
                    rotateY: rightTilt.isHovered ? rightTilt.x : -2,
                    rotateX: rightTilt.isHovered ? rightTilt.y : 0,
                    scale: rightTilt.isHovered ? 1.04 : 1.025,
                  }
              }
              style={{
                z: reducedMotion ? 0 : rightCardZ,
                rotateY: reducedMotion ? 0 : rightCardRotateY,
                scale: reducedMotion ? 1 : rightCardScale,
                transformStyle: "preserve-3d",
              }}
              transition={{ type: "spring", stiffness: 280, damping: 24 }}
              className={`relative h-full bg-white border-2 border-navy rounded-[8px] p-8 flex flex-col justify-between overflow-hidden ${reducedMotion ? "shadow-[6px_6px_0_0_#0F2B4A]" : ""
                }`}
            >
              {/* Dynamic Specular Glass Highlight on Hover */}
              {rightTilt.isHovered && !reducedMotion && (
                <div
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] pointer-events-none z-20"
                  style={{
                    background: `radial-gradient(circle 160px at ${rightTilt.px}% ${rightTilt.py}%, rgba(255,255,255,0.7) 0%, transparent 80%)`,
                  }}
                />
              )}

              <div>
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-cobalt block mb-3">
                  CURIO FEYNMAN SYSTEM
                </span>

                {/* Arrow Chain Title */}
                <h3 className="font-heading text-xl font-bold text-navy mb-4">
                  Explain → Question → Discover Gaps → Master
                </h3>

                <ul className="space-y-3.5 font-sans text-sm text-navy/85">
                  <motion.li
                    initial={reducedMotion ? {} : { opacity: 0, x: 8 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.1, duration: 0.4 }}
                    className="flex items-start gap-2.5"
                  >
                    <span className="text-cobalt font-bold inline-block select-none">✓</span>
                    <span>Teaching forces your brain to structure and articulate mental models.</span>
                  </motion.li>

                  {/* Orange Gap Bullet with Soft Glow Moment */}
                  <motion.li
                    initial={reducedMotion ? {} : { opacity: 0, x: 8 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.25, duration: 0.4 }}
                    className="flex items-start gap-2.5 relative"
                  >
                    <div className="relative">
                      <span className="text-gap-orange font-bold inline-block select-none">✓</span>
                      <span
                        aria-hidden="true"
                        className="absolute -inset-1 rounded-full bg-gap-orange/25 animate-ping pointer-events-none"
                        style={{ animationDuration: "2.2s" }}
                      />
                    </div>
                    <span>Curio actively probes your explanations for exact logical gaps and misconceptions.</span>
                  </motion.li>

                  <motion.li
                    initial={reducedMotion ? {} : { opacity: 0, x: 8 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.4, duration: 0.4 }}
                    className="flex items-start gap-2.5"
                  >
                    <span className="text-cobalt font-bold inline-block select-none">✓</span>
                    <span>Generates a 3D isometric Gap Report mapping exactly what needs deliberate practice.</span>
                  </motion.li>
                </ul>
              </div>

              {/* Decorative Text-Free Isometric Gap Laboratory Platform */}
              <IsometricGapLaboratory />
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
