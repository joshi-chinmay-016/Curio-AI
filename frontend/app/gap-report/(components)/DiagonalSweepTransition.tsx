"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export function DiagonalSweepTransition() {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(false), 700);
    return () => clearTimeout(timer);
  }, []);

  if (!isVisible) return null;

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
