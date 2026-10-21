"use client";

import React, { memo } from "react";

interface PenguinCohortProps {
  scale?: number;
  reducedMotion?: boolean;
}

interface CompanionConfig {
  id: string;
  x: number; // offset from center
  y: number; // offset from center
  scale: number;
  flip: boolean;
  delay: string;
  dur: string;
  zIndex: number;
}

const COMPANIONS: CompanionConfig[] = [
  // Back row (tallest / peeking from behind)
  { id: "c-back-center", x: 2, y: -26, scale: 0.94, flip: false, delay: "0s", dur: "3.2s", zIndex: 1 },
  { id: "c-back-left", x: -25, y: -21, scale: 0.90, flip: false, delay: "0.5s", dur: "3.4s", zIndex: 2 },
  { id: "c-back-right", x: 27, y: -21, scale: 0.88, flip: true, delay: "0.9s", dur: "3.1s", zIndex: 2 },

  // Flank / Side row
  { id: "c-far-left", x: -52, y: -7, scale: 0.82, flip: false, delay: "0.3s", dur: "3.5s", zIndex: 3 },
  { id: "c-mid-left", x: -30, y: -2, scale: 0.86, flip: false, delay: "0.7s", dur: "3.0s", zIndex: 4 },
  { id: "c-mid-right", x: 34, y: -4, scale: 0.84, flip: true, delay: "0.2s", dur: "3.3s", zIndex: 4 },
  { id: "c-far-right", x: 56, y: 3, scale: 0.78, flip: true, delay: "1.1s", dur: "3.6s", zIndex: 3 },

  // Front-right outer companion
  { id: "c-front-right", x: 44, y: 13, scale: 0.74, flip: true, delay: "0.6s", dur: "2.9s", zIndex: 5 },
];

export const PenguinCohort = memo(function PenguinCohort({
  scale = 1,
  reducedMotion = false,
}: PenguinCohortProps) {
  return (
    <div
      className="relative select-none pointer-events-none"
      style={{
        width: `${48 * scale}px`,
        height: `${56 * scale}px`,
      }}
    >
      <style jsx>{`
        @keyframes cohort-breathe {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-1.8px);
          }
        }
        .anim-cohort-penguin {
          animation: cohort-breathe var(--dur, 3s) ease-in-out infinite;
          animation-delay: var(--delay, 0s);
          transform-origin: center bottom;
        }
      `}</style>

      {/* Shared Ground Shadow for the Cohort */}
      <svg
        className="absolute pointer-events-none"
        style={{
          width: `${170 * scale}px`,
          height: `${38 * scale}px`,
          left: `${(24 - 85) * scale}px`,
          top: `${(52 - 19) * scale}px`,
          overflow: "visible",
          zIndex: 0,
        }}
        viewBox="0 0 170 38"
        fill="none"
      >
        <defs>
          <filter id="cohort-shadow-blur" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" />
          </filter>
        </defs>
        <ellipse
          cx="85"
          cy="19"
          rx="72"
          ry="13"
          fill="#0B1C33"
          opacity="0.28"
          filter="url(#cohort-shadow-blur)"
        />
      </svg>

      {/* Companion Penguins Group */}
      {COMPANIONS.map((comp) => {
        const pScale = comp.scale * scale;
        const width = 48 * pScale;
        const height = 56 * pScale;
        const left = (24 + comp.x) * scale - width / 2;
        const top = (52 + comp.y) * scale - height;

        return (
          <div
            key={comp.id}
            className={`absolute pointer-events-none select-none ${
              reducedMotion ? "" : "anim-cohort-penguin"
            }`}
            style={
              {
                left: `${left}px`,
                top: `${top}px`,
                width: `${width}px`,
                height: `${height}px`,
                zIndex: comp.zIndex,
                transform: comp.flip ? "scaleX(-1)" : "none",
                transformOrigin: "center bottom",
                "--delay": comp.delay,
                "--dur": comp.dur,
              } as React.CSSProperties
            }
          >
            <svg
              width="100%"
              height="100%"
              viewBox="0 0 48 56"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <filter id={`sh-${comp.id}`} x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="1.2" />
                </filter>
              </defs>

              {/* Individual Ground Contact Shadow */}
              <ellipse
                cx="24"
                cy="52"
                rx="12.5"
                ry="3"
                fill="#0A182B"
                opacity="0.25"
                filter={`url(#sh-${comp.id})`}
              />

              {/* Left Foot */}
              <path
                d="M14 47 C13 47.5, 10 50.5, 9.5 52 C9 53.2, 11 53.8, 14 53 C16.5 52.2, 18 49.5, 17.5 48 Z"
                fill="#FF7A29"
              />
              <path
                d="M10.5 52 C12 51.5, 14 52.5, 15.5 52"
                stroke="#E05B0D"
                strokeWidth="0.8"
                strokeLinecap="round"
              />

              {/* Right Foot */}
              <path
                d="M30.5 47 C31.5 47.5, 34.5 50.5, 35 52 C35.5 53.2, 33.5 53.8, 30.5 53 C28 52.2, 26.5 49.5, 27 48 Z"
                fill="#FF7A29"
              />
              <path
                d="M34 52 C32.5 51.5, 30.5 52.5, 29 52"
                stroke="#E05B0D"
                strokeWidth="0.8"
                strokeLinecap="round"
              />

              {/* Left Wing (Back Flipper) */}
              <path
                d="M11 25 C7 27.5, 5 35, 8.5 38.5 C11 39.5, 13 34, 13.5 28.5 Z"
                fill="#0A182B"
              />

              {/* Penguin Body Torso (Deep Navy) */}
              <ellipse cx="24" cy="30" rx="14" ry="18.5" fill="#0D1F38" />

              {/* Penguin Head */}
              <circle cx="24" cy="17" r="11" fill="#0D1F38" />

              {/* Helmet / Visor Base (Cobalt Indigo) */}
              <path
                d="M 13.8 15.2 C 13.8 9.5, 34.2 9.5, 34.2 15.2 C 34.2 22, 31 27, 24 28 C 17 27, 13.8 22, 13.8 15.2 Z"
                fill="#2C3B75"
              />

              {/* Visor Top Rim Reflection Highlight */}
              <path
                d="M 15.5 13.8 C 19 11, 29 11, 32.5 13.8"
                stroke="#4F60AA"
                strokeWidth="1.2"
                strokeLinecap="round"
              />

              {/* Distinctive Cohort "T" Visor Emblem (Glowing Lavender/Periwinkle) */}
              {/* Horizontal Bar */}
              <path
                d="M 17.5 17.5 L 30.5 17.5"
                stroke="#7A8FFF"
                strokeWidth="2.6"
                strokeLinecap="round"
              />
              {/* Vertical Slit */}
              <path
                d="M 24 17.5 L 24 25.5"
                stroke="#7A8FFF"
                strokeWidth="2.6"
                strokeLinecap="round"
              />
              {/* Bright Core Line */}
              <path
                d="M 18.5 17.5 L 29.5 17.5"
                stroke="#A8B5FF"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
              <path
                d="M 24 18 L 24 25"
                stroke="#A8B5FF"
                strokeWidth="1.2"
                strokeLinecap="round"
              />

              {/* Small Orange Beak at Base of Visor */}
              <path
                d="M 24 24.8 L 21.8 28 C 23.2 28.6, 24.8 28.6, 26.2 28 Z"
                fill="#FF7A29"
              />
              <path
                d="M 24 24.8 L 24 28.3"
                stroke="#E05B0D"
                strokeWidth="0.5"
                strokeLinecap="round"
              />

              {/* Right Wing (Front Flipper) */}
              <path
                d="M 34.5 25 C 38.5 27.5, 40.5 35, 37 38.5 C 34.5 39.5, 32.5 34, 32 28.5 Z"
                fill="#0D1F38"
              />
            </svg>
          </div>
        );
      })}
    </div>
  );
});
