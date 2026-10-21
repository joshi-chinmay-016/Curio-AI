"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LogOut,
  Mic,
  Menu,
  X,
  Layers,
  FileText,
  BookOpen,
  Sliders,
  Sparkles,
  Users,
  LayoutDashboard,
  Sun,
  Moon,
} from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { useAuthStore } from "@/stores/authStore";
import { useSettingsStore } from "@/stores/settingsStore";
import { ProfileDropdown } from "@/components/curio/profile/ProfileDropdown";

export type CurioNavRoute =
  | "home"
  | "dashboard"
  | "audio-learning"
  | "documents"
  | "topics"
  | "history"
  | "characters"
  | "settings";

export interface CurioNavProps {
  activeRoute?: CurioNavRoute;
}

export function CurioNav({ activeRoute = "home" }: CurioNavProps) {
  const router = useRouter();
  const { user, isAuthenticated, initAuth, logout } = useAuthStore();
  const { theme, setTheme } = useSettingsStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  const navLinks = [
    {
      id: "dashboard",
      label: "DASHBOARD",
      href: "/dashboard",
      icon: LayoutDashboard,
      requiresAuth: true,
    },
    {
      id: "audio-learning",
      label: "AUDIO LEARNING",
      href: "/audio-learning",
      icon: Mic,
      iconColor: "text-gap-orange",
      requiresAuth: true,
    },
    {
      id: "documents",
      label: "DOCUMENTS",
      href: "/documents",
      icon: FileText,
      requiresAuth: true,
    },
    {
      id: "topics",
      label: "TOPICS",
      href: "/topics",
      icon: Sparkles,
      requiresAuth: false,
    },
    {
      id: "history",
      label: "HISTORY",
      href: "/history",
      icon: BookOpen,
      requiresAuth: false,
    },
    {
      id: "characters",
      label: "CHARACTERS",
      href: "/characters",
      icon: Users,
      requiresAuth: false,
    },
    {
      id: "settings",
      label: "SETTINGS",
      href: "/settings",
      icon: Sliders,
      requiresAuth: false,
    },
  ];

  const visibleLinks = navLinks.filter(
    (item) => !item.requiresAuth || isAuthenticated
  );

  return (
    <header className="w-full bg-white/95 backdrop-blur-[4px] border-b border-fog sticky top-0 z-40 px-4 md:px-6 py-3 shadow-xs">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo & Desktop Nav Links */}
        <div className="flex items-center gap-6 lg:gap-8">
          <Link
            href="/"
            className="font-mono text-xl font-bold tracking-wider text-navy hover:text-cobalt transition-colors shrink-0"
          >
            CURIO<span className="text-gap-orange">.</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-4 xl:gap-5 text-xs font-mono font-semibold uppercase tracking-wider">
            {visibleLinks.map((item) => {
              const isActive = activeRoute === item.id;
              const Icon = item.icon;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={`inline-flex items-center gap-1.5 pb-0.5 transition-colors ${
                    isActive
                      ? "text-cobalt border-b-2 border-cobalt font-bold"
                      : "text-navy/70 hover:text-navy"
                  }`}
                >
                  {Icon && (
                    <Icon
                      className={`w-3.5 h-3.5 ${
                        item.iconColor || (isActive ? "text-cobalt" : "text-navy/50")
                      }`}
                    />
                  )}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Actions & Auth */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          {/* GitHub link */}
          <a
            href="https://github.com/joshi-chinmay-016/Curio-AI"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Curio AI on GitHub"
            className="hidden sm:inline-flex p-2 text-navy/70 hover:text-navy hover:bg-ice/80 rounded-md transition-colors"
            title="GitHub Repository"
          >
            <svg
              role="img"
              viewBox="0 0 24 24"
              className="w-4 h-4 fill-current"
              xmlns="http://www.w3.org/2000/svg"
            >
              <title>GitHub</title>
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
          </a>

          {isAuthenticated ? (
            <div className="flex items-center gap-2 sm:gap-3">
              {activeRoute !== "dashboard" && (
                <Link href="/dashboard" className="hidden sm:inline-block">
                  <KeycapButton variant="navy" size="sm">
                    DASHBOARD →
                  </KeycapButton>
                </Link>
              )}

              {/* Top AI Product Profile Trigger & Menu */}
              <ProfileDropdown />
            </div>
          ) : (
            <div className="flex items-center gap-2 sm:gap-2.5">
              <ProfileDropdown />
              <Link href="/login" className="hidden sm:inline-block">
                <KeycapButton variant="ghost" size="sm">
                  SIGN IN
                </KeycapButton>
              </Link>
              <Link href="/register">
                <KeycapButton variant="navy" size="sm">
                  GET STARTED →
                </KeycapButton>
              </Link>
            </div>
          )}

          {/* Mobile Hamburger Toggle */}
          <button
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="p-1.5 text-navy/70 hover:text-navy hover:bg-ice rounded-[4px] lg:hidden cursor-pointer"
            aria-label="Toggle navigation menu"
            title="Navigation Menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden mt-3 pt-3 border-t border-fog/80 animate-fade-in">
          <nav className="flex flex-col gap-1 text-xs font-mono font-semibold uppercase">
            {visibleLinks.map((item) => {
              const isActive = activeRoute === item.id;
              const Icon = item.icon;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-[4px] transition-colors ${
                    isActive
                      ? "bg-navy text-white font-bold"
                      : "text-navy/80 hover:bg-ice hover:text-navy"
                  }`}
                >
                  {Icon && (
                    <Icon
                      className={`w-4 h-4 ${
                        isActive
                          ? "text-gap-orange"
                          : item.iconColor || "text-navy/50"
                      }`}
                    />
                  )}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Quick Theme Switcher in Mobile Drawer */}
          <div className="pt-3 mt-2 border-t border-fog/60 flex items-center justify-between px-2 py-1">
            <span className="text-[11px] font-mono text-navy/60 font-bold uppercase">
              THEME:
            </span>
            <div className="inline-flex items-center gap-1 bg-white border border-fog p-0.5 rounded-[4px]">
              <button
                type="button"
                onClick={() => setTheme("light")}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-[3px] text-[10px] font-mono font-bold uppercase transition-all ${
                  theme === "light"
                    ? "bg-navy text-white shadow-xs"
                    : "text-navy/60 hover:text-navy hover:bg-ice"
                }`}
              >
                <Sun className="w-3 h-3" />
                <span>LIGHT</span>
              </button>
              <button
                type="button"
                onClick={() => setTheme("dark")}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-[3px] text-[10px] font-mono font-bold uppercase transition-all ${
                  theme === "dark"
                    ? "bg-cobalt text-white shadow-xs"
                    : "text-navy/60 hover:text-navy hover:bg-ice"
                }`}
              >
                <Moon className="w-3 h-3" />
                <span>DARK</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
