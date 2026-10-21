"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";

export function TypewriterHeadline() {
  const fullSentence = "If you can't teach it, You don't know it.";
  const splitIndex = 23; // "If you can't teach it, " has 23 characters

  // Current typed character count
  const [charIndex, setCharIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const [cursorVisible, setCursorVisible] = useState(true);

  // Blinking mechanical typewriter cursor (450ms rhythm)
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setCursorVisible((v) => !v);
    }, 450);
    return () => clearInterval(blinkInterval);
  }, []);

  // Typewriter engine: steady, rhythmic keypresses one letter at a time
  useEffect(() => {
    let timer: NodeJS.Timeout;

    if (!isDeleting) {
      // TYPING FORWARD: 1 by 1
      if (charIndex < fullSentence.length) {
        // Steady, tactile speed: 75ms per character
        // Deliberate pause on the comma after "teach it," (380ms)
        const isMiddleComma = charIndex === 21;
        const delay = isMiddleComma ? 380 : 75;

        timer = setTimeout(() => {
          setCharIndex((prev) => prev + 1);
        }, delay);
      } else {
        // Complete sentence: hold in mid-air for 4.5 seconds for reading
        timer = setTimeout(() => {
          setIsDeleting(true);
        }, 4500);
      }
    } else {
      // DELETING BACKWARD
      if (charIndex > 0) {
        timer = setTimeout(() => {
          setCharIndex((prev) => prev - 1);
        }, 24);
      } else {
        // Pause at empty before beginning to type again
        timer = setTimeout(() => {
          setIsDeleting(false);
        }, 650);
      }
    }

    return () => clearTimeout(timer);
  }, [charIndex, isDeleting, fullSentence.length]);

  // Derive visible text chunks
  // Part 1: "If you can't teach it,"
  const part1 = fullSentence.slice(0, Math.min(charIndex, 22));
  // Line break / second line trigger
  const hasSecondLine = charIndex >= splitIndex;
  // Part 2: "You don't know it."
  const part2 = charIndex >= splitIndex ? fullSentence.slice(splitIndex, charIndex) : "";

  return (
    <motion.h1
      className="font-heading text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy dark:text-[#F0F4F8] tracking-tight leading-[1.08] mb-6 min-h-[2.2em]"
      aria-label="If you can't teach it, You don't know it."
      animate={{
        y: [0, -3.5, 0],
      }}
      transition={{
        duration: 5,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      <span className="text-navy dark:text-[#F0F4F8] block sm:inline">{part1}</span>
      {hasSecondLine && <br className="hidden sm:inline" />}
      {hasSecondLine && <span className="sm:hidden"> </span>}
      {part2 && (
        <span className="text-cobalt italic tracking-tight">{part2}</span>
      )}
      {/* Typewriter Cursor: sits right after the active letter */}
      <span
        aria-hidden="true"
        className={`inline-block w-[3.5px] sm:w-[4.5px] h-[0.85em] bg-cobalt ml-1 align-baseline rounded-[1px] transition-opacity duration-75 shadow-[0_0_8px_rgba(30,58,138,0.3)] ${
          cursorVisible ? "opacity-100" : "opacity-0"
        }`}
      />
    </motion.h1>
  );
}
