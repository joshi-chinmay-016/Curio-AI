"use client";

import React, { useRef, useState, useEffect, useMemo, useCallback } from "react";
import { useReducedMotion } from "framer-motion";
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

  // Page dimensions
  const [pageDims, setPageDims] = useState<{ width: number; height: number }>({
    width: 1200,
    height: 6000,
  });
  const [mounted, setMounted] = useState<boolean>(false);

  const reducedMotion = mounted ? Boolean(reducedMotionRaw) : false;

  // Active section tint
  const [activeTint, setActiveTint] = useState<string>(SECTION_TINTS[0].tint);

  // Penguin state
  const [penguinPos, setPenguinPos] = useState<{ x: number; y: number }>({ x: 90, y: 135 });
  const [facingRight, setFacingRight] = useState<boolean>(true);
  const [penguinOpacity, setPenguinOpacity] = useState<number>(1);
  const [isMoving, setIsMoving] = useState<boolean>(false);
  const [velocityScale, setVelocityScale] = useState<number>(1);

  // Measure page dimensions
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

    const timer = setTimeout(updateDimensions, 300);

    return () => {
      window.removeEventListener("resize", handleResize);
      ro.disconnect();
      clearTimeout(timer);
    };
  }, [updateDimensions]);

  // Construct organic S-curve SVG path winding down the page starting at top
  const pathData = useMemo(() => {
    const { width: w, height: h } = pageDims;
    const isMobile = w < 768;

    const leftX = isMobile ? w * 0.22 : Math.max(90, w * 0.14);
    const rightX = isMobile ? w * 0.78 : Math.min(w - 90, w * 0.86);
    const midX = w * 0.5;

    // Waypoints from top of hero down to final CTA:
    const p0 = { x: isMobile ? 36 : Math.max(48, w * 0.08), y: 135 };
    const p1 = { x: rightX, y: h * 0.20 };
    const p2 = { x: leftX, y: h * 0.36 };
    const p3 = { x: rightX * 0.95, y: h * 0.52 };
    const p4 = { x: leftX * 1.15, y: h * 0.67 };
    const p5 = { x: isMobile ? midX * 1.2 : w * 0.76, y: h * 0.82 };
    const p6 = { x: isMobile ? midX : w * 0.45, y: h * 0.93 };

    return `M ${p0.x} ${p0.y} ` +
      `C ${p0.x + (p1.x - p0.x) * 0.4} ${p0.y + (p1.y - p0.y) * 0.2}, ${p1.x - (p1.x - p0.x) * 0.4} ${p1.y - (p1.y - p0.y) * 0.3}, ${p1.x} ${p1.y} ` +
      `C ${p1.x + (p2.x - p1.x) * 0.4} ${p1.y + (p2.y - p1.y) * 0.25}, ${p2.x - (p2.x - p1.x) * 0.4} ${p2.y - (p2.y - p1.y) * 0.25}, ${p2.x} ${p2.y} ` +
      `C ${p2.x + (p3.x - p2.x) * 0.4} ${p2.y + (p3.y - p2.y) * 0.25}, ${p3.x - (p3.x - p2.x) * 0.4} ${p3.y - (p3.y - p2.y) * 0.25}, ${p3.x} ${p3.y} ` +
      `C ${p3.x + (p4.x - p3.x) * 0.4} ${p4.y + (p4.y - p3.y) * 0.25}, ${p4.x - (p4.x - p3.x) * 0.4} ${p4.y - (p4.y - p3.y) * 0.25}, ${p4.x} ${p4.y} ` +
      `C ${p4.x + (p5.x - p4.x) * 0.4} ${p5.y + (p5.y - p4.y) * 0.25}, ${p5.x - (p5.x - p4.x) * 0.4} ${p5.y - (p5.y - p4.y) * 0.25}, ${p5.x} ${p5.y} ` +
      `C ${p5.x + (p6.x - p5.x) * 0.4} ${p5.y + (p6.y - p5.y) * 0.3}, ${p6.x} ${p6.y - (p6.y - p5.y) * 0.2}, ${p6.x} ${p6.y}`;
  }, [pageDims]);

  // Section boundary detection
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

  // Update position directly from scroll events
  useEffect(() => {
    let lastScrollY = window.scrollY || 0;
    let stopMovingTimer: NodeJS.Timeout;

    const handleScroll = () => {
      if (!pathRef.current) return;
      const totalLen = pathRef.current.getTotalLength();
      if (!totalLen || totalLen <= 0) return;

      const scrollY = window.scrollY || window.pageYOffset || 0;
      const maxScroll = Math.max(
        1,
        (document.documentElement.scrollHeight || document.body.scrollHeight) - window.innerHeight
      );
      const progress = Math.min(1, Math.max(0, scrollY / maxScroll));

      // Calculate motion velocity for waddle cycle
      const delta = Math.abs(scrollY - lastScrollY);
      lastScrollY = scrollY;
      if (delta > 0.5) {
        setIsMoving(true);
        setVelocityScale(Math.min(2.2, 1 + delta / 18));
        clearTimeout(stopMovingTimer);
        stopMovingTimer = setTimeout(() => {
          setIsMoving(false);
        }, 140);
      }

      // Check section tint
      checkActiveSection();

      // Travel progress along path [0, 0.94]
      const endProgress = 0.94;
      const t = Math.max(0, Math.min(1, progress / endProgress));
      const targetDist = t * totalLen;

      try {
        const p0 = pathRef.current.getPointAtLength(targetDist);
        const lookaheadDist = Math.min(targetDist + 8, totalLen);
        const p1 = pathRef.current.getPointAtLength(lookaheadDist);

        const dx = p1.x - p0.x;
        if (dx > 0.25) {
          setFacingRight(true);
        } else if (dx < -0.25) {
          setFacingRight(false);
        }

        setPenguinPos({ x: p0.x, y: p0.y });

        // Fade out before final CTA
        if (progress > endProgress) {
          setPenguinOpacity(Math.max(0, 1 - (progress - endProgress) / 0.05));
        } else {
          setPenguinOpacity(1);
        }
      } catch (e) {
        // Point calculation fallback
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    // Immediate call to position penguin at scroll = 0
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
      clearTimeout(stopMovingTimer);
    };
  }, [checkActiveSection, pathData]);

  if (!mounted) return null;

  const penguinScale = pageDims.width < 768 ? 0.82 : 1;

  return (
    <>
      {/* 1. BACKGROUND TINT LAYER (Fixed, full-bleed at -z-10, perfectly behind page content) */}
      <div
        aria-hidden="true"
        className="fixed inset-0 pointer-events-none -z-10 transition-colors duration-700 ease-out"
        style={{
          backgroundColor: activeTint,
        }}
      />

      {/* 2. THE PATH & PENGUIN LAYER (Pointer events none, crisp, zero blur overlays) */}
      <div
        ref={containerRef}
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none select-none overflow-hidden z-[15]"
        style={{ height: `${pageDims.height}px` }}
      >
        {/* Continuous Dotted SVG Trajectory */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ height: `${pageDims.height}px` }}
        >
          <defs>
            <linearGradient id="pathGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3A63FF" stopOpacity="0.25" />
              <stop offset="15%" stopColor="#3A63FF" stopOpacity="0.35" />
              <stop offset="85%" stopColor="#3A63FF" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#3A63FF" stopOpacity="0.12" />
            </linearGradient>
          </defs>

          <path
            ref={pathRef}
            d={pathData}
            fill="none"
            stroke="url(#pathGradient)"
            strokeWidth={pageDims.width < 768 ? "2" : "2.5"}
            strokeDasharray="6 8"
            strokeLinecap="round"
          />
        </svg>

        {/* The Penguin Mascot */}
        <div
          className="absolute pointer-events-none select-none transition-opacity duration-200"
          style={{
            transform: `translate3d(${penguinPos.x - 24 * penguinScale}px, ${
              penguinPos.y - 52 * penguinScale
            }px, 0)`,
            opacity: penguinOpacity,
            willChange: "transform, opacity",
          }}
        >
          <PenguinTraveler
            facingRight={facingRight}
            isMoving={isMoving}
            velocityScale={velocityScale}
            reducedMotion={reducedMotion}
            scale={penguinScale}
          />
        </div>
      </div>
    </>
  );
}
