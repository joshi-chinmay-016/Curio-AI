"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, ArrowRight, Lock, Mail, AlertCircle, CheckCircle2, User } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { useAuthStore } from "@/stores/authStore";

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading, error, clearError, initAuth } = useAuthStore();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      initAuth();
    }
  }, [isAuthenticated, initAuth]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isLoading, isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setFormError(null);

    const cleanName = name.trim();
    const cleanEmail = email.trim();

    // 1. Validations
    if (!cleanName) {
      setFormError("Please enter your full name.");
      return;
    }
    if (!cleanEmail) {
      setFormError("Please enter your email address.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      setFormError("Please enter a valid RFC-compliant email address.");
      return;
    }
    if (!password) {
      setFormError("Please provide a password.");
      return;
    }
    if (password.length < 8) {
      setFormError("Password must be at least 8 characters in length.");
      return;
    }
    if (password !== confirmPassword) {
      setFormError("Passwords do not match. Please re-enter.");
      return;
    }

    try {
      setIsSubmitting(true);
      await register({ name: cleanName, email: cleanEmail, password });
      router.replace("/dashboard");
    } catch (err: any) {
      setIsSubmitting(false);
    }
  };

  const displayedError = formError || error;

  return (
    <div className="min-h-screen bg-ice dark:bg-[#070D18] text-navy dark:text-[#F0F4F8] flex flex-col selection:bg-cobalt selection:text-white relative">
      <DiagonalSweepTransition />

      {/* Top Navbar */}
      <header className="w-full bg-white/80 dark:bg-[#080F1A]/95 backdrop-blur-sm border-b border-fog dark:border-[#1E3652] px-4 md:px-6 py-3.5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 font-mono text-xs uppercase font-semibold text-navy/70 dark:text-[#C5D0DE] hover:text-navy dark:hover:text-white transition-colors px-2.5 py-1 bg-ice/60 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[4px]"
            >
              <ArrowRight className="w-3.5 h-3.5 rotate-180" />
              <span>HOME</span>
            </Link>

            <Link
              href="/"
              className="font-mono text-xl font-bold tracking-wider text-navy dark:text-[#F0F4F8] hover:text-cobalt dark:hover:text-[#4D7CFF] transition-colors"
            >
              CURIO<span className="text-gap-orange">.</span>
            </Link>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="hidden sm:flex items-center gap-3 text-navy/60 dark:text-[#829AB1]">
              <Link href="/topics" className="hover:text-navy dark:hover:text-white transition-colors">
                TOPICS
              </Link>
              <Link href="/characters" className="hover:text-navy dark:hover:text-white transition-colors">
                CHARACTERS
              </Link>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-navy/50 dark:text-[#829AB1] hidden md:inline">ALREADY HAVE AN ACCOUNT?</span>
              <Link href="/login" className="text-cobalt dark:text-[#4D7CFF] font-bold hover:underline">
                SIGN IN →
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          {/* Card Frame */}
          <div className="bg-white dark:bg-[#0E1A2B] border-2 border-navy dark:border-[#2F4D73] rounded-[10px] p-8 md:p-10 shadow-[8px_8px_0_0_#0F2B4A] dark:shadow-[8px_8px_0_0_#040910] relative">
            {/* Top Accent Tag */}
            <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-ice dark:bg-[#16273F] rounded-[4px] border border-fog/80 dark:border-[#2F4D73] text-[10px] font-mono uppercase tracking-widest text-navy/70 dark:text-[#C5D0DE] font-bold mb-6">
              <span className="w-2 h-2 rounded-full bg-gap-orange inline-block animate-pulse" />
              NEW LEARNER ENROLLMENT
            </div>

            <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-navy dark:text-[#F0F4F8] tracking-tight mb-2">
              Start learning by teaching.
            </h1>
            <p className="font-sans text-sm text-navy/70 dark:text-[#BAC7D5] mb-8 leading-relaxed">
              Create an account to track your concept models, unmask knowledge gaps, and record persistent progress.
            </p>

            {/* Error Banner */}
            {displayedError && (
              <div
                role="alert"
                className="mb-6 p-4 bg-red-50 dark:bg-rose-950/50 border border-red-200 dark:border-rose-800 rounded-[8px] text-red-800 dark:text-rose-300 text-xs font-sans leading-relaxed"
              >
                <div className="flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-red-600 dark:text-rose-400 shrink-0 mt-0.5" />
                  <span className="font-medium">{displayedError}</span>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {/* Full Name */}
              <div>
                <label
                  htmlFor="name"
                  className="block font-mono text-xs font-bold uppercase tracking-wider text-navy/80 dark:text-[#C5D0DE] mb-2"
                >
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-navy/40 dark:text-[#829AB1] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    id="name"
                    name="name"
                    type="text"
                    autoComplete="name"
                    required
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (displayedError) {
                        clearError();
                        setFormError(null);
                      }
                    }}
                    placeholder="e.g. Richard Feynman"
                    className="w-full pl-10 pr-4 py-2.5 bg-ice/40 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[6px] font-sans text-sm text-navy dark:text-[#F0F4F8] placeholder:text-navy/35 dark:placeholder:text-[#627D98] focus:outline-none focus:border-cobalt focus:ring-1 focus:ring-cobalt transition-colors"
                  />
                </div>
              </div>

              {/* Email Address */}
              <div>
                <label
                  htmlFor="email"
                  className="block font-mono text-xs font-bold uppercase tracking-wider text-navy/80 dark:text-[#C5D0DE] mb-2"
                >
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-navy/40 dark:text-[#829AB1] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (displayedError) {
                        clearError();
                        setFormError(null);
                      }
                    }}
                    placeholder="learner@feynman.edu"
                    className="w-full pl-10 pr-4 py-2.5 bg-ice/40 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[6px] font-sans text-sm text-navy dark:text-[#F0F4F8] placeholder:text-navy/35 dark:placeholder:text-[#627D98] focus:outline-none focus:border-cobalt focus:ring-1 focus:ring-cobalt transition-colors"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="password"
                  className="block font-mono text-xs font-bold uppercase tracking-wider text-navy/80 dark:text-[#C5D0DE] mb-2"
                >
                  Password (min. 8 characters)
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-navy/40 dark:text-[#829AB1] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (displayedError) {
                        clearError();
                        setFormError(null);
                      }
                    }}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-11 py-2.5 bg-ice/40 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[6px] font-sans text-sm text-navy dark:text-[#F0F4F8] placeholder:text-navy/35 dark:placeholder:text-[#627D98] focus:outline-none focus:border-cobalt focus:ring-1 focus:ring-cobalt transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-navy/40 dark:text-[#829AB1] hover:text-navy dark:hover:text-white p-1 transition-colors"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block font-mono text-xs font-bold uppercase tracking-wider text-navy/80 dark:text-[#C5D0DE] mb-2"
                >
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-navy/40 dark:text-[#829AB1] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (displayedError) {
                        clearError();
                        setFormError(null);
                      }
                    }}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-11 py-2.5 bg-ice/40 dark:bg-[#101F33] border border-fog dark:border-[#1E3652] rounded-[6px] font-sans text-sm text-navy dark:text-[#F0F4F8] placeholder:text-navy/35 dark:placeholder:text-[#627D98] focus:outline-none focus:border-cobalt focus:ring-1 focus:ring-cobalt transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-navy/40 dark:text-[#829AB1] hover:text-navy dark:hover:text-white p-1 transition-colors"
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Password Requirement Hint */}
              <div className="flex items-center gap-2 pt-1 text-[11px] font-mono text-navy/60 dark:text-[#829AB1]">
                <CheckCircle2 className={`w-3.5 h-3.5 ${password.length >= 8 ? "text-emerald-600 dark:text-emerald-400" : "text-navy/30 dark:text-[#829AB1]/40"}`} />
                <span>Minimum 8 characters required</span>
              </div>

              {/* Submit Action */}
              <div className="pt-3">
                <KeycapButton
                  variant="navy"
                  size="lg"
                  className="w-full justify-center"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      CREATING ACCOUNT...
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      CREATE ACCOUNT <ArrowRight className="w-4 h-4" />
                    </span>
                  )}
                </KeycapButton>
              </div>
            </form>

            {/* Bottom Nav */}
            <div className="mt-8 pt-6 border-t border-fog/60 dark:border-[#1E3652] text-center text-xs font-sans text-navy/70 dark:text-[#BAC7D5]">
              Already have an account?{" "}
              <Link href="/login" className="font-bold text-cobalt dark:text-[#4D7CFF] hover:underline">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
