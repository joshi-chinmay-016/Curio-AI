"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  Sliders,
  Mic,
  Moon,
  Sun,
  Laptop,
  LogOut,
  ChevronDown,
  Sparkles,
  BookOpen,
  ArrowRight,
  Shield,
  Layers,
  Award,
  Zap,
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useSettingsStore } from "@/stores/settingsStore";
import { AppTheme } from "@/types/settings";

export function ProfileDropdown() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { user, isAuthenticated, logout } = useAuthStore();
  const {
    theme,
    setTheme,
    profile,
    learning,
    stats,
    initSettings,
  } = useSettingsStore();

  useEffect(() => {
    initSettings();
  }, [initSettings]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const displayName = user?.name || profile.displayName || (user?.email ? user.email.split("@")[0] : "Learner");
  const displayEmail = user?.email || profile.email || "learner@curio.ai";
  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const handleLogout = () => {
    setIsOpen(false);
    logout();
    router.push("/login");
  };

  const handleThemeChange = (newTheme: AppTheme) => {
    setTheme(newTheme);
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* Profile Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-[5px] border border-fog/80 bg-white hover:bg-ice/80 hover:border-navy/40 transition-all cursor-pointer shadow-xs active:translate-y-[1px]"
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label="User profile and settings"
      >
        {/* Avatar Monogram with Status indicator */}
        <div className="relative w-7 h-7 rounded-[4px] bg-navy text-white flex items-center justify-center font-mono text-xs font-bold border border-navy shadow-[1px_1px_0_0_#0F2B4A]">
          {profile.characterAvatar === "STUDENT"
            ? "🎓"
            : profile.characterAvatar === "TEACHER"
            ? "📐"
            : profile.characterAvatar === "PROFESSOR"
            ? "⚡"
            : initials}
          <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 border border-white" />
        </div>

        {/* Name and Level badge */}
        <div className="hidden sm:flex flex-col text-left leading-tight">
          <span className="font-sans text-xs font-bold text-navy truncate max-w-[110px]">
            {displayName}
          </span>
          <span className="font-mono text-[9px] font-semibold text-cobalt uppercase tracking-wider">
            LVL {profile.feynmanLevel} • PRO
          </span>
        </div>

        <ChevronDown
          className={`w-3.5 h-3.5 text-navy/60 transition-transform duration-200 ${
            isOpen ? "rotate-180 text-navy" : ""
          }`}
        />
      </button>

      {/* Popover Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -6 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute right-0 mt-2 w-80 sm:w-88 rounded-[6px] bg-white border-2 border-navy shadow-editorial z-50 overflow-hidden divide-y divide-fog/60"
          >
            {/* 1. Header: Profile Identity */}
            <div className="p-4 bg-gradient-to-b from-ice/40 to-white">
              <div className="flex items-start gap-3">
                <div className="w-11 h-11 rounded-[6px] bg-navy text-white flex items-center justify-center font-mono text-base font-bold shrink-0 border-2 border-navy shadow-[2px_2px_0_0_#0F2B4A]">
                  {profile.characterAvatar === "STUDENT"
                    ? "🎓"
                    : profile.characterAvatar === "TEACHER"
                    ? "📐"
                    : profile.characterAvatar === "PROFESSOR"
                    ? "⚡"
                    : initials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h4 className="font-heading text-sm font-bold text-navy truncate">
                      {displayName}
                    </h4>
                    <span className="font-mono text-[9px] font-bold uppercase bg-gap-orange text-white px-1.5 py-0.2 rounded-[2px] tracking-wider shrink-0">
                      PRO
                    </span>
                  </div>
                  <p className="font-mono text-[11px] text-navy/60 truncate">
                    {displayEmail}
                  </p>
                  <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono text-cobalt font-semibold">
                    <Award className="w-3 h-3 shrink-0" />
                    <span>{profile.levelTitle}</span>
                  </div>
                </div>
              </div>

              {/* 3 Quick Learner Metrics */}
              <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-fog/60 text-center">
                <div className="bg-ice/60 border border-fog/60 rounded-[4px] py-1.5 px-1">
                  <div className="font-mono text-xs font-bold text-gap-orange">
                    {stats.gapsResolved}
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-wider text-navy/60">
                    Gaps Fixed
                  </div>
                </div>
                <div className="bg-ice/60 border border-fog/60 rounded-[4px] py-1.5 px-1">
                  <div className="font-mono text-xs font-bold text-cobalt">
                    {stats.conceptsMastered}
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-wider text-navy/60">
                    Mastered
                  </div>
                </div>
                <div className="bg-ice/60 border border-fog/60 rounded-[4px] py-1.5 px-1">
                  <div className="font-mono text-xs font-bold text-navy">
                    {stats.feynmanStreakDays}d 🔥
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-wider text-navy/60">
                    Streak
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Theme Toggle Switcher Bar */}
            <div className="px-4 py-2.5 bg-ice/30 flex items-center justify-between">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/60 flex items-center gap-1.5">
                {theme === "dark" ? (
                  <Moon className="w-3 h-3 text-cobalt" />
                ) : theme === "light" ? (
                  <Sun className="w-3 h-3 text-gap-orange" />
                ) : (
                  <Laptop className="w-3 h-3 text-navy/60" />
                )}
                APPEARANCE
              </span>

              {/* 3-Way Pill Switch */}
              <div className="inline-flex items-center p-0.5 bg-white border border-fog rounded-[4px] shadow-xs">
                <button
                  type="button"
                  onClick={() => handleThemeChange("light")}
                  className={`flex items-center gap-1 px-2 py-1 rounded-[3px] font-mono text-[10px] font-bold uppercase transition-all ${
                    theme === "light"
                      ? "bg-navy text-white shadow-xs"
                      : "text-navy/60 hover:text-navy hover:bg-ice"
                  }`}
                  title="Light Editorial Theme"
                >
                  <Sun className="w-3 h-3" />
                  <span className="hidden sm:inline">Light</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleThemeChange("system")}
                  className={`flex items-center gap-1 px-2 py-1 rounded-[3px] font-mono text-[10px] font-bold uppercase transition-all ${
                    theme === "system"
                      ? "bg-navy text-white shadow-xs"
                      : "text-navy/60 hover:text-navy hover:bg-ice"
                  }`}
                  title="Follow OS Theme"
                >
                  <Laptop className="w-3 h-3" />
                  <span className="hidden sm:inline">Auto</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleThemeChange("dark")}
                  className={`flex items-center gap-1 px-2 py-1 rounded-[3px] font-mono text-[10px] font-bold uppercase transition-all ${
                    theme === "dark"
                      ? "bg-cobalt text-white shadow-xs"
                      : "text-navy/60 hover:text-navy hover:bg-ice"
                  }`}
                  title="Dark Blueprint Theme"
                >
                  <Moon className="w-3 h-3" />
                  <span className="hidden sm:inline">Dark</span>
                </button>
              </div>
            </div>

            {/* 3. Primary Actions Under Profile */}
            <div className="p-2 space-y-0.5">
              <Link
                href="/settings?tab=profile"
                onClick={() => setIsOpen(false)}
                className="flex items-center justify-between px-3 py-2 rounded-[4px] text-xs font-mono font-medium text-navy/80 hover:text-navy hover:bg-ice transition-colors group"
              >
                <div className="flex items-center gap-2.5">
                  <User className="w-4 h-4 text-cobalt" />
                  <span>Profile & Avatar</span>
                </div>
                <ArrowRight className="w-3 h-3 text-navy/40 group-hover:text-navy group-hover:translate-x-0.5 transition-all" />
              </Link>

              <Link
                href="/settings?tab=learning"
                onClick={() => setIsOpen(false)}
                className="flex items-center justify-between px-3 py-2 rounded-[4px] text-xs font-mono font-medium text-navy/80 hover:text-navy hover:bg-ice transition-colors group"
              >
                <div className="flex items-center gap-2.5">
                  <Sliders className="w-4 h-4 text-gap-orange" />
                  <span>Feynman Rigor & Probing</span>
                </div>
                <span className="font-mono text-[10px] font-bold uppercase text-navy/40 bg-ice px-1.5 py-0.5 rounded border border-fog/60">
                  {learning.rigorLevel}
                </span>
              </Link>

              <Link
                href="/settings?tab=audio"
                onClick={() => setIsOpen(false)}
                className="flex items-center justify-between px-3 py-2 rounded-[4px] text-xs font-mono font-medium text-navy/80 hover:text-navy hover:bg-ice transition-colors group"
              >
                <div className="flex items-center gap-2.5">
                  <Mic className="w-4 h-4 text-cobalt" />
                  <span>Voice & Persona Studio</span>
                </div>
                <ArrowRight className="w-3 h-3 text-navy/40 group-hover:text-navy group-hover:translate-x-0.5 transition-all" />
              </Link>

              <Link
                href="/gap-report"
                onClick={() => setIsOpen(false)}
                className="flex items-center justify-between px-3 py-2 rounded-[4px] text-xs font-mono font-medium text-navy/80 hover:text-navy hover:bg-ice transition-colors group"
              >
                <div className="flex items-center gap-2.5">
                  <Sparkles className="w-4 h-4 text-gap-orange" />
                  <span>Interactive 3D Knowledge Map</span>
                </div>
                <span className="font-mono text-[9px] font-bold text-gap-orange bg-gap-orange/10 px-1.5 py-0.5 rounded border border-gap-orange/20">
                  MAP
                </span>
              </Link>
            </div>

            {/* 4. Footer Actions & Sign Out */}
            <div className="p-2 bg-ice/40 flex items-center justify-between">
              <span className="font-mono text-[10px] text-navy/40">
                Curio AI v2.5.0
              </span>

              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-[4px] font-mono text-xs font-bold text-red-600 hover:text-red-700 hover:bg-red-50 border border-transparent hover:border-red-200 transition-colors cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>SIGN OUT</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
