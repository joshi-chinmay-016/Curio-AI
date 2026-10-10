"use client";

import React, { memo } from "react";

interface PenguinTravelerProps {
  facingRight?: boolean;
  isMoving?: boolean;
  velocityScale?: number;
  reducedMotion?: boolean;
  scale?: number;
}

export const PenguinTraveler = memo(function PenguinTraveler({
  facingRight = true,
  isMoving = false,
  velocityScale = 1,
  reducedMotion = false,
  scale = 1,
}: PenguinTravelerProps) {
  // Speed bounds: from ~0.35s (fast scroll) to ~0.70s (idle waddle)
  const animDuration = reducedMotion
    ? "0s"
    : isMoving
    ? `${Math.max(0.35, Math.min(0.65, 0.65 / velocityScale)).toFixed(2)}s`
    : "0.72s";

  return (
    <div
      className="relative select-none pointer-events-none"
      style={{
        width: `${48 * scale}px`,
        height: `${56 * scale}px`,
        transform: `scaleX(${facingRight ? 1 : -1})`,
        transformOrigin: "center bottom",
        transition: reducedMotion ? "none" : "transform 0.18s cubic-bezier(0.2, 0.8, 0.4, 1)",
      }}
    >
      <style jsx>{`
        @keyframes waddle-body {
          0%, 100% {
            transform: translateY(0px) rotate(-4.5deg);
          }
          50% {
            transform: translateY(-2.5px) rotate(4.5deg);
          }
        }
        @keyframes waddle-foot-left {
          0%, 100% {
            transform: translateY(0px) translateX(-0.5px) rotate(5deg);
          }
          50% {
            transform: translateY(-2.5px) translateX(1.5px) rotate(-3deg);
          }
        }
        @keyframes waddle-foot-right {
          0%, 100% {
            transform: translateY(-2.5px) translateX(1.5px) rotate(-3deg);
          }
          50% {
            transform: translateY(0px) translateX(-0.5px) rotate(5deg);
          }
        }
        @keyframes waddle-flipper-left {
          0%, 100% {
            transform: rotate(10deg);
          }
          50% {
            transform: rotate(-7deg);
          }
        }
        @keyframes waddle-flipper-right {
          0%, 100% {
            transform: rotate(-7deg);
          }
          50% {
            transform: rotate(10deg);
          }
        }
        @keyframes shadow-pulse {
          0%, 100% {
            transform: scale(0.96);
            opacity: 0.18;
          }
          50% {
            transform: scale(1.05);
            opacity: 0.12;
          }
        }

        .anim-body {
          animation: waddle-body var(--anim-dur) ease-in-out infinite;
          transform-origin: 24px 46px;
        }
        .anim-foot-left {
          animation: waddle-foot-left var(--anim-dur) ease-in-out infinite;
          transform-origin: 16px 50px;
        }
        .anim-foot-right {
          animation: waddle-foot-right var(--anim-dur) ease-in-out infinite;
          transform-origin: 32px 50px;
        }
        .anim-flipper-left {
          animation: waddle-flipper-left var(--anim-dur) ease-in-out infinite;
          transform-origin: 13px 26px;
        }
        .anim-flipper-right {
          animation: waddle-flipper-right var(--anim-dur) ease-in-out infinite;
          transform-origin: 35px 26px;
        }
        .anim-shadow {
          animation: shadow-pulse var(--anim-dur) ease-in-out infinite;
          transform-origin: 24px 53px;
        }
      `}</style>

      <svg
        width="100%"
        height="100%"
        viewBox="0 0 48 56"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={
          {
            "--anim-dur": animDuration,
          } as React.CSSProperties
        }
      >
        <defs>
          <filter id="shadow-blur" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="1.5" />
          </filter>
        </defs>

        {/* 1. Ground Contact Shadow Ellipse */}
        <ellipse
          cx="24"
          cy="52.5"
          rx="13.5"
          ry="3.2"
          fill="#0F2B4A"
          filter="url(#shadow-blur)"
          className={reducedMotion ? "" : "anim-shadow"}
        />

        {/* 2. Left Foot (Back Foot) */}
        <g className={reducedMotion ? "" : "anim-foot-left"}>
          <path
            d="M14 47 C13 47.5, 9.5 50.5, 9 52 C8.5 53.2, 10.5 53.8, 13.5 53 C16.5 52.2, 18 49.5, 17.5 48 Z"
            fill="#FF7A29"
          />
          <path
            d="M10 52 C11.5 51.5, 14 52.5, 15.5 52"
            stroke="#E05B0D"
            strokeWidth="0.8"
            strokeLinecap="round"
          />
        </g>

        {/* 3. Right Foot (Front Foot) */}
        <g className={reducedMotion ? "" : "anim-foot-right"}>
          <path
            d="M30.5 47 C31.5 47.5, 35 50.5, 35.5 52 C36 53.2, 34 53.8, 31 53 C28 52.2, 26.5 49.5, 27 48 Z"
            fill="#FF7A29"
          />
          <path
            d="M34.5 52 C33 51.5, 30.5 52.5, 29 52"
            stroke="#E05B0D"
            strokeWidth="0.8"
            strokeLinecap="round"
          />
        </g>

        {/* 4. Main Body & Head Group */}
        <g className={reducedMotion ? "" : "anim-body"}>
          {/* Left Flipper (Back Wing) */}
          <path
            className={reducedMotion ? "" : "anim-flipper-left"}
            d="M11.5 25 C7.5 27.5, 5.5 35, 9 38.5 C11.5 39.5, 13.5 34, 14 28.5 Z"
            fill="#0B2038"
          />

          {/* Main Penguin Torso (Curio Deep Navy) */}
          <ellipse cx="24" cy="30" rx="14" ry="18.5" fill="#0F2B4A" />

          {/* Penguin Head */}
          <circle cx="24" cy="17" r="11" fill="#0F2B4A" />

          {/* Clean White Belly Patch */}
          <ellipse cx="24" cy="33.5" rx="9.8" ry="13.2" fill="#FFFFFF" />

          {/* White Eye Rings / Mask (Subtle Curious Expression) */}
          <circle cx="20" cy="16.5" r="3.6" fill="#FFFFFF" />
          <circle cx="28" cy="16.5" r="3.6" fill="#FFFFFF" />

          {/* Eyes (Deep Navy pupils with high-light reflection) */}
          <circle cx="20.5" cy="16.5" r="1.6" fill="#0F2B4A" />
          <circle cx="21" cy="16" r="0.6" fill="#FFFFFF" />

          <circle cx="27.5" cy="16.5" r="1.6" fill="#0F2B4A" />
          <circle cx="28" cy="16" r="0.6" fill="#FFFFFF" />

          {/* Cute subtle blue-tint cheeks (Curio cobalt accent at 18%) */}
          <ellipse cx="17.5" cy="19" rx="1.6" ry="1" fill="#3A63FF" opacity="0.22" />
          <ellipse cx="30.5" cy="19" rx="1.6" ry="1" fill="#3A63FF" opacity="0.22" />

          {/* Orange Beak (Curio Gap-Orange) */}
          <path
            d="M24 17.5 L21.2 21 C22.8 21.6, 25.2 21.6, 26.8 21 Z"
            fill="#FF7A29"
          />
          <path
            d="M24 17.5 L24 21.3"
            stroke="#E05B0D"
            strokeWidth="0.6"
            strokeLinecap="round"
          />

          {/* Right Flipper (Front Wing) */}
          <path
            className={reducedMotion ? "" : "anim-flipper-right"}
            d="M34.5 25 C38.5 27.5, 40.5 35, 37 38.5 C34.5 39.5, 32.5 34, 32 28.5 Z"
            fill="#0F2B4A"
          />
        </g>
      </svg>
    </div>
  );
});
