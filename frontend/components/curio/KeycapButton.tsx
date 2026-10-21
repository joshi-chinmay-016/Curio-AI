"use client";

import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface KeycapButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  loading?: boolean;
  loadingText?: string;
  variant?: "default" | "gap" | "cobalt" | "resolve" | "navy" | "ghost" | "ghost-orange";
  size?: "sm" | "md" | "lg";
}

export function KeycapButton({
  children,
  onClick,
  loading = false,
  loadingText,
  disabled = false,
  variant = "default",
  size = "md",
  className,
  ...props
}: KeycapButtonProps) {
  const [isPressed, setIsPressed] = useState(false);

  const baseStyles =
    "inline-flex items-center justify-center font-mono font-semibold uppercase tracking-wider select-none rounded-[4px] border-2 transition-all duration-75 cursor-pointer disabled:cursor-not-allowed disabled:opacity-60";

  const sizeStyles = {
    sm: "text-[11px] px-3 py-1.5 min-h-[30px] gap-1.5 shadow-[0_3px_0_0_currentColor] dark:shadow-[0_3px_0_0_rgba(0,0,0,0.7)]",
    md: "text-xs md:text-sm px-5 py-2.5 min-h-[42px] gap-2 shadow-[0_4px_0_0_currentColor,0_6px_12px_rgba(15,43,74,0.1)] dark:shadow-[0_4px_0_0_rgba(0,0,0,0.7),0_6px_12px_rgba(0,0,0,0.5)]",
    lg: "text-sm md:text-base px-6 py-3 min-h-[48px] gap-2.5 shadow-[0_5px_0_0_currentColor,0_8px_16px_rgba(15,43,74,0.15)] dark:shadow-[0_5px_0_0_rgba(0,0,0,0.7),0_8px_16px_rgba(0,0,0,0.5)]",
  };

  const variantStyles = {
    default: {
      normal:
        "border-navy dark:border-[#2F4D73] bg-white dark:bg-[#101F33] text-navy dark:text-[#F0F4F8] hover:bg-navy dark:hover:bg-cobalt hover:text-white dark:hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#0F2B4A] dark:shadow-[0_0px_0_0_#040910]",
    },
    navy: {
      normal:
        "border-navy dark:border-cobalt bg-navy dark:bg-cobalt text-white hover:bg-[#183d66] dark:hover:bg-[#2F52E0] hover:border-[#183d66] dark:hover:border-[#2F52E0]",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#0F2B4A] dark:shadow-[0_0px_0_0_#040910]",
    },
    gap: {
      normal:
        "border-gap-orange bg-white dark:bg-[#101F33] text-gap-orange hover:bg-gap-orange hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#FF6B1A]",
    },
    cobalt: {
      normal:
        "border-cobalt bg-white dark:bg-[#101F33] text-cobalt hover:bg-cobalt hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#3A63FF]",
    },
    resolve: {
      normal:
        "border-cobalt bg-white dark:bg-[#101F33] text-cobalt hover:bg-cobalt hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#3A63FF]",
    },
    ghost: {
      normal:
        "border-navy dark:border-[#2F4D73] bg-transparent text-navy dark:text-[#F0F4F8] hover:bg-navy dark:hover:bg-[#101F33] hover:text-white dark:hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#0F2B4A] dark:shadow-[0_0px_0_0_#040910]",
    },
    "ghost-orange": {
      normal:
        "border-navy dark:border-[#2F4D73] bg-transparent text-navy dark:text-[#F0F4F8] hover:bg-gap-orange hover:border-gap-orange hover:text-white dark:hover:bg-gap-orange dark:hover:border-gap-orange dark:hover:text-white hover:shadow-[0_5px_0_0_#CC5200,0_8px_18px_rgba(255,107,26,0.3)] dark:hover:shadow-[0_5px_0_0_#CC5200,0_8px_18px_rgba(0,0,0,0.7)]",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#CC5200]",
    },
  };

  const activeVariant = variantStyles[variant] || variantStyles.default;

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onMouseLeave={() => setIsPressed(false)}
      onKeyDown={(e) => {
        if (e.key === " " || e.key === "Enter") {
          setIsPressed(true);
        }
      }}
      onKeyUp={() => setIsPressed(false)}
      className={cn(
        baseStyles,
        sizeStyles[size],
        activeVariant.normal,
        isPressed && !disabled && !loading && activeVariant.pressed,
        loading && "opacity-80 translate-y-[2px] shadow-[0_2px_0_0_currentColor]",
        className
      )}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>{loadingText || "LOADING..."}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
