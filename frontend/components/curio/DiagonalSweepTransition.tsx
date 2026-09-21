"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

export function DiagonalSweepTransition() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  if (prefersReducedMotion) {
    return (
      <motion.div
        initial={{ opacity: 1 }}
        animate={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        style={{
          position: "fixed",
          inset: 0,
          background: "#0F2B4A",
          zIndex: 9999,
          pointerEvents: "none",
        }}
      />
    );
  }

  return (
    <motion.div
      initial={{ clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)" }}
      animate={{ clipPath: "polygon(100% 0, 100% 0, 100% 100%, 100% 100%)" }}
      transition={{ duration: 0.6, ease: [0.76, 0, 0.24, 1] }}
      style={{
        position: "fixed",
        inset: 0,
        background: "#0F2B4A",
        zIndex: 9999,
        pointerEvents: "none",
      }}
    />
  );
}
