"use client";

import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface KeycapButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  loading?: boolean;
  variant?: "default" | "gap" | "resolve";
  size?: "sm" | "md";
}

export function KeycapButton({
  children,
  onClick,
  loading = false,
  disabled = false,
  variant = "default",
  size = "md",
  className,
  ...props
}: KeycapButtonProps) {
  const [isPressed, setIsPressed] = useState(false);

  const baseStyles =
    "inline-flex items-center justify-center font-mono font-semibold uppercase tracking-wider select-none rounded-[6px] transition-all duration-75 cursor-pointer disabled:cursor-not-allowed disabled:opacity-60";

  const sizeStyles = {
    sm: "text-xs px-3 py-1.5 min-h-[32px] gap-1.5",
    md: "text-xs md:text-sm px-5 py-2.5 min-h-[42px] gap-2",
  };

  const variantStyles = {
    default: {
      normal:
        "border-2 border-navy bg-white text-navy shadow-[0_4px_0_0_#0F2B4A,0_6px_12px_rgba(0,0,0,0.1)] hover:bg-navy hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#0F2B4A]",
    },
    gap: {
      normal:
        "border-2 border-gap-orange bg-white text-gap-orange shadow-[0_4px_0_0_#FF6B1A,0_6px_12px_rgba(255,107,26,0.15)] hover:bg-gap-orange hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#FF6B1A]",
    },
    resolve: {
      normal:
        "border-2 border-cobalt bg-white text-cobalt shadow-[0_4px_0_0_#3A63FF,0_6px_12px_rgba(58,99,255,0.15)] hover:bg-cobalt hover:text-white",
      pressed: "translate-y-1 shadow-[0_0px_0_0_#3A63FF]",
    },
  };

  const activeVariant = variantStyles[variant];

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onMouseLeave={() => setIsPressed(false)}
      className={cn(
        baseStyles,
        sizeStyles[size],
        activeVariant.normal,
        isPressed && !disabled && !loading && activeVariant.pressed,
        loading && "translate-y-[2px] shadow-[0_2px_0_0_currentColor]",
        className
      )}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>LOADING...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
