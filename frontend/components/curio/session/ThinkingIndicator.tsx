"use client";

import React from "react";
import { motion } from "framer-motion";

export function ThinkingIndicator() {
  const dotVariants = {
    initial: { opacity: 0.2 },
    animate: { opacity: 1 },
  };

  return (
    <div className="flex justify-start w-full my-2">
      <div className="bg-white border border-fog rounded-[2px_8px_8px_8px] px-4 py-2.5 flex items-center gap-1.5 shadow-sm">
        <span className="font-mono text-xs uppercase tracking-wider text-navy/60 mr-1">
          CURIO IS THINKING
        </span>
        <motion.span
          variants={dotVariants}
          initial="initial"
          animate="animate"
          transition={{
            repeat: Infinity,
            repeatType: "reverse",
            duration: 0.5,
            delay: 0,
          }}
          className="font-mono text-sm font-bold text-cobalt"
        >
          .
        </motion.span>
        <motion.span
          variants={dotVariants}
          initial="initial"
          animate="animate"
          transition={{
            repeat: Infinity,
            repeatType: "reverse",
            duration: 0.5,
            delay: 0.18,
          }}
          className="font-mono text-sm font-bold text-cobalt"
        >
          .
        </motion.span>
        <motion.span
          variants={dotVariants}
          initial="initial"
          animate="animate"
          transition={{
            repeat: Infinity,
            repeatType: "reverse",
            duration: 0.5,
            delay: 0.36,
          }}
          className="font-mono text-sm font-bold text-cobalt"
        >
          .
        </motion.span>
      </div>
    </div>
  );
}
