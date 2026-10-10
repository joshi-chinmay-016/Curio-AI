"use client";

import React, { useRef, useState, useEffect, useMemo, useCallback } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  useVelocity,
  useReducedMotion,
  useMotionValueEvent,
} from "framer-motion";
import { PenguinTraveler } from "./PenguinTraveler";

interface SectionTint {
  id: string;
  tint: string;
}

const SECTION_TINTS: SectionTint[] = [
  { id: "hero-section", tint: "#E8EEF3" }, // Curio Ice
  { id: "how-it-works", tint: "#FFFFFF" }, // White / Clean
  { id: "how-curio-thinks", tint: "#EBF3FA" }, // Pale Cobalt / Ice
  { id: "adaptive-network", tint: "#F3F6FA" }, // Pale Navy Mist
  { id: "teacher-mode-demo", tint: "#FFF8F2" }, // Very soft warm accent
  { id: "report-preview", tint: "#E8EEF3" }, // Curio Ice
  { id: "final-cta", tint: "#FFFFFF" }, // White
];

export function ScrollJourneyLayer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const reducedMotionRaw = useReducedMotion();

  // Dimensions state
  const [pageDims, setPageDims] = useState<{ width: number; height: number }>({
    width: 1200,
    height: 6000,
  });
  const [pathTotalLength, setPathTotalLength] = useState<number>(0);
  const [mounted, setMounted] = useState<boolean>(false);

  const reducedMotion = mounted ? Boolean(reducedMotionRaw) : false;

  // Active section tint state
  const [activeTint, setActiveTint] = useState<string>(SECTION_TINTS[0].tint);

  // Penguin state
  const [penguinPos, setPenguinPos] = useState<{ x: number; y: number }>({ x: 200, y: 500 });
  const [facingRight, setFacingRight] = useState<boolean>(true);
  const [penguinOpacity, setPenguinOpacity] = useState<number>(0);
  const [isMoving, setIsMoving] = useState<boolean>(false);
  const [velocityScale, setVelocityScale] = useState<number>(1);

  // Single page-level scroll progress
  const { scrollYProgress } = useScroll();
  const scrollVelocity = useVelocity(scrollYProgress);

  // Spring smoothed progress for organic mascot movement
  const springProgress = useSpring(scrollYProgress, {
    stiffness: 110,
    damping: 24,
    restDelta: 0.0005,
  });

  // Path drawing progress (Framer Motion pathLength)
  const pathDrawProgress = useTransform(scrollYProgress, [0.06, 0.90], [0, 1]);

  // Measure page dimensions reliably
  const updateDimensions = useCallback(() => {
    if (typeof window === "undefined") return;
    const body = document.body;
    const html = document.documentElement;
    const h = Math.max(
      body.scrollHeight,
      body.offsetHeight,
      html.clientHeight,
      html.scrollHeight,
      html.offsetHeight
    );
    const w = window.innerWidth;
    setPageDims({ width: w, height: h });
  }, []);

  useEffect(() => {
    setMounted(true);
    updateDimensions();

    const handleResize = () => {
      updateDimensions();
    };

    window.addEventListener("resize", handleResize);
    const ro = new ResizeObserver(() => {
      updateDimensions();
    });
    ro.observe(document.body);

    // Initial timeout to capture dynamically hydrated 3D sections
    const timer = setTimeout(updateDimensions, 400);

    return () => {
      window.removeEventListener("resize", handleResize);
      ro.disconnect();
      clearTimeout(timer);
    };
  }, [updateDimensions]);

  // Construct organic S-curve SVG path winding down the page
  const pathData = useMemo(() => {
    const { width: w, height: h } = pageDims;
    const isMobile = w < 768;

    // Boundary X coordinates
    // Desktop: gentle swing between ~18% and ~82%
    // Mobile: narrower path (~28% to ~72%) so it never overlaps narrow screen edges
    const leftX = isMobile ? w * 0.28 : Math.max(120, w * 0.16);
    const rightX = isMobile ? w * 0.72 : Math.min(w - 120, w * 0.84);
    const midX = w * 0.5;

    // Vertical anchor waypoints matching the landing page journey:
    // 1. After Hero headline (~8% down)
    // 2. Learning Paradox entrance (~22%)
    // 3. How Curio Thinks / Feynman Loop top (~38%)
    // 4. Feynman Loop center (~54%)
    // 5. Adaptive Network (~68%)
    // 6. Teacher Mode & Report Preview (~82%)
    // 7. Before Final CTA (~92%)
    const p0 = { x: isMobile ? midX * 0.7 : w * 0.22, y: h * 0.08 };
    const p1 = { x: rightX, y: h * 0.22 };
    const p2 = { x: leftX, y: h * 0.38 };
    const p3 = { x: rightX * 0.95, y: h * 0.54 };
    const p4 = { x: leftX * 1.1, y: h * 0.68 };
    const p5 = { x: isMobile ? midX * 1.3 : w * 0.78, y: h * 0.82 };
    const p6 = { x: isMobile ? midX : w * 0.42, y: h * 0.92 };

    return `M ${p0.x} ${p0.y} ` +
      `C ${p0.x + (p1.x - p0.x) * 0.4} ${p0.y + (p1.y - p0.y) * 0.2}, ${p1.x - (p1.x - p0.x) * 0.4} ${p1.y - (p1.y - p0.y) * 0.3}, ${p1.x} ${p1.y} ` +
      `C ${p1.x + (p2.x - p1.x) * 0.4} ${p1.y + (p2.y - p1.y) * 0.25}, ${p2.x - (p2.x - p1.x) * 0.4} ${p2.y - (p2.y - p1.y) * 0.25}, ${p2.x} ${p2.y} ` +
      `C ${p2.x + (p3.x - p2.x) * 0.4} ${p2.y + (p3.y - p2.y) * 0.25}, ${p3.x - (p3.x - p2.x) * 0.4} ${p3.y - (p3.y - p2.y) * 0.25}, ${p3.x} ${p3.y} ` +
      `C ${p3.x + (p4.x - p3.x) * 0.4} ${p3.y + (p4.y - p3.y) * 0.25}, ${p4.x - (p4.x - p3.x) * 0.4} ${p4.y - (p4.y - p3.y) * 0.25}, ${p4.x} ${p4.y} ` +
      `C ${p4.x + (p5.x - p4.x) * 0.4} ${p4.y + (p5.y - p4.y) * 0.25}, ${p5.x - (p5.x - p4.x) * 0.4} ${p5.y - (p5.y - p4.y) * 0.25}, ${p5.x} ${p5.y} ` +
      `C ${p5.x + (p6.x - p5.x) * 0.4} ${p5.y + (p6.y - p5.y) * 0.3}, ${p6.x} ${p6.y - (p6.y - p5.y) * 0.2}, ${p6.x} ${p6.y}`;
  }, [pageDims]);

  // Cache path total length
  useEffect(() => {
    if (pathRef.current) {
      try {
        const len = pathRef.current.getTotalLength();
        setPathTotalLength(len);
      } catch (e) {
        // SVG not rendered yet
      }
    }
  }, [pathData, mounted]);

  // Section boundary detection for background sync
  const checkActiveSection = useCallback(() => {
    if (typeof window === "undefined") return;
    const scrollY = window.scrollY || window.pageYOffset;
    const viewportMiddle = scrollY + window.innerHeight * 0.45;

    let foundTint = SECTION_TINTS[0].tint;

    for (let i = SECTION_TINTS.length - 1; i >= 0; i--) {
      const sec = document.getElementById(SECTION_TINTS[i].id);
      if (sec) {
        const top = sec.offsetTop;
        if (viewportMiddle >= top - 60) {
          foundTint = SECTION_TINTS[i].tint;
          break;
        }
      }
    }

    setActiveTint(foundTint);
  }, []);

  // Update penguin position, tangent orientation, and section tint on scroll
  useMotionValueEvent(springProgress, "change", (latestSpring) => {
    if (reducedMotion || !pathRef.current || pathTotalLength <= 0) return;

    // Check section tint sync
    checkActiveSection();

    // Map scroll progress to path travel range [0.07, 0.92]
    const startProgress = 0.07;
    const endProgress = 0.92;

    if (latestSpring < startProgress) {
      setPenguinOpacity(0);
      return;
    }

    // Fade in after hero
    if (latestSpring >= startProgress && latestSpring < startProgress + 0.05) {
      setPenguinOpacity((latestSpring - startProgress) / 0.05);
    } else if (latestSpring >= endProgress && latestSpring <= endProgress + 0.04) {
      // Fade out before final CTA
      setPenguinOpacity(1 - (latestSpring - endProgress) / 0.04);
    } else if (latestSpring > endProgress + 0.04) {
      setPenguinOpacity(0);
      return;
    } else {
      setPenguinOpacity(1);
    }

    // Normalized progress along the path [0, 1]
    const t = Math.max(0, Math.min(1, (latestSpring - startProgress) / (endProgress - startProgress)));
    const targetDist = t * pathTotalLength;

    try {
      const p0 = pathRef.current.getPointAtLength(targetDist);
      const lookaheadDist = Math.min(targetDist + 6, pathTotalLength);
      const p1 = pathRef.current.getPointAtLength(lookaheadDist);

      // Tangent vector dx determines horizontal orientation
      const dx = p1.x - p0.x;
      if (dx > 0.4) {
        setFacingRight(true);
      } else if (dx < -0.4) {
        setFacingRight(false);
      }

      setPenguinPos({ x: p0.x, y: p0.y });
    } catch (e) {
      // Point lookup safety
    }
  });

  // Track velocity to modulate waddle cycle speed
  useMotionValueEvent(scrollVelocity, "change", (v) => {
    if (reducedMotion) return;
    const absV = Math.abs(v);
    setIsMoving(absV > 0.0006);
    setVelocityScale(1 + Math.min(1.4, absV * 25));
  });

  // Ambient parallax drift values
  const parallax1 = useTransform(scrollYProgress, [0, 1], [-30, 80]);
  const parallax2 = useTransform(scrollYProgress, [0, 1], [50, -90]);

  if (!mounted) return null;

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className="absolute inset-0 pointer-events-none select-none overflow-hidden z-[5]"
      style={{ height: `${pageDims.height}px` }}
    >
      {/* ═════════════════════════════════════════════════════════════════ */}
      {/* 1. BACKGROUND TINT LAYER (Fixed, full-bleed, smooth crossfade)    */}
      {/* ═════════════════════════════════════════════════════════════════ */}
      <div
        className="fixed inset-0 pointer-events-none -z-10 transition-colors duration-700 ease-out"
        style={{
          backgroundColor: activeTint,
          opacity: 0.85,
        }}
      />

      {/* ═════════════════════════════════════════════════════════════════ */}
      {/* 2. AMBIENT DEPTH LAYER (Low-opacity soft drifting contours)       */}
      {/* ═════════════════════════════════════════════════════════════════ */}
      {!reducedMotion && pageDims.width >= 768 && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden -z-[1]">
          {/* Subtle Ambient Shape 1 */}
          <motion.div
            style={{ y: parallax1 }}
            className="absolute top-[28%] left-[8%] w-80 h-80 rounded-full border border-cobalt/10 bg-cobalt/[0.03] blur-xl"
          />
          {/* Subtle Ambient Shape 2 */}
          <motion.div
            style={{ y: parallax2 }}
            className="absolute top-[65%] right-[10%] w-96 h-96 rounded-full border border-navy/10 bg-navy/[0.02] blur-xl"
          />
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════ */}
      {/* 3. THE PATH (Curio Cobalt Accent Dotted SVG)                      */}
      {/* ═════════════════════════════════════════════════════════════════ */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ height: `${pageDims.height}px` }}
      >
        <defs>
          <linearGradient id="pathGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3A63FF" stopOpacity="0.1" />
            <stop offset="10%" stopColor="#3A63FF" stopOpacity="0.25" />
            <stop offset="85%" stopColor="#3A63FF" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#3A63FF" stopOpacity="0.08" />
          </linearGradient>
        </defs>

        {/* Dynamic winding path */}
        <motion.path
          ref={pathRef}
          d={pathData}
          fill="none"
          stroke="url(#pathGradient)"
          strokeWidth={pageDims.width < 768 ? "2" : "2.5"}
          strokeDasharray="6 8"
          strokeLinecap="round"
          style={
            reducedMotion
              ? { pathLength: 1, opacity: 0.6 }
              : {
                  pathLength: pathDrawProgress,
                  opacity: 1,
                }
          }
        />
      </svg>

      {/* ═════════════════════════════════════════════════════════════════ */}
      {/* 4. THE PENGUIN TRAVELER                                           */}
      {/* ═════════════════════════════════════════════════════════════════ */}
      {reducedMotion ? (
        // Still pose for reduced motion users
        <div
          className="absolute"
          style={{
            left: `${pageDims.width * 0.5 - 24}px`,
            top: `${pageDims.height * 0.45 - 52}px`,
            opacity: 0.85,
          }}
        >
          <PenguinTraveler
            facingRight={true}
            isMoving={false}
            reducedMotion={true}
            scale={pageDims.width < 768 ? 0.82 : 1}
          />
        </div>
      ) : (
        // Dynamic scroll-following penguin
        <div
          className="absolute transition-opacity duration-200"
          style={{
            transform: `translate3d(${penguinPos.x - 24 * (pageDims.width < 768 ? 0.82 : 1)}px, ${
              penguinPos.y - 52 * (pageDims.width < 768 ? 0.82 : 1)
            }px, 0)`,
            opacity: penguinOpacity,
            willChange: "transform, opacity",
          }}
        >
          <PenguinTraveler
            facingRight={facingRight}
            isMoving={isMoving}
            velocityScale={velocityScale}
            reducedMotion={false}
            scale={pageDims.width < 768 ? 0.82 : 1}
          />
        </div>
      )}
    </div>
  );
}
