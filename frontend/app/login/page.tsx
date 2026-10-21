"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, ArrowRight, Lock, Mail, AlertCircle, Sparkles } from "lucide-react";
import { KeycapButton } from "@/components/curio/KeycapButton";
import { DiagonalSweepTransition } from "@/components/curio/DiagonalSweepTransition";
import { useAuthStore } from "@/stores/authStore";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = searchParams.get("returnTo") || "/dashboard";

  const { login, loginDemoUser, isAuthenticated, isLoading, error, clearError, initAuth } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      initAuth();
    }
  }, [isAuthenticated, initAuth]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(returnTo);
    }
  }, [isLoading, isAuthenticated, router, returnTo]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setFormError(null);

    // Client-side validations
    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setFormError("Please enter your email address.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      setFormError("Please enter a valid email address.");
      return;
    }
    if (!password) {
      setFormError("Please enter your password.");
      return;
    }

    try {
      setIsSubmitting(true);
      await login({ email: cleanEmail, password });
      router.replace(returnTo);
    } catch (err: any) {
      setIsSubmitting(false);
      // error is already captured in authStore
    }
  };

  const displayedError = formError || error;

  return (
    <div className="min-h-screen bg-ice text-navy flex flex-col selection:bg-cobalt selection:text-white relative">
      <DiagonalSweepTransition />

      {/* Top Navbar */}
      <header className="w-full bg-white/80 backdrop-blur-sm border-b border-fog px-4 md:px-6 py-3.5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 font-mono text-xs uppercase font-semibold text-navy/70 hover:text-navy transition-colors px-2.5 py-1 bg-ice/60 border border-fog rounded-[4px]"
            >
              <ArrowRight className="w-3.5 h-3.5 rotate-180" />
              <span>HOME</span>
            </Link>

            <Link
              href="/"
              className="font-mono text-xl font-bold tracking-wider text-navy hover:text-cobalt transition-colors"
            >
              CURIO<span className="text-gap-orange">.</span>
            </Link>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="hidden sm:flex items-center gap-3 text-navy/60">
              <Link href="/topics" className="hover:text-navy transition-colors">
                TOPICS
              </Link>
              <Link href="/characters" className="hover:text-navy transition-colors">
                CHARACTERS
              </Link>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-navy/50 hidden md:inline">NEW TO CURIO?</span>
              <Link href="/register" className="text-cobalt font-bold hover:underline">
                CREATE ACCOUNT →
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Authentication Container */}
      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          {/* Card Frame */}
          <div className="bg-white border-2 border-navy rounded-[10px] p-8 md:p-10 shadow-[8px_8px_0_0_#0F2B4A] relative">
            {/* Top Accent Tag */}
            <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-ice rounded-[4px] border border-fog/80 text-[10px] font-mono uppercase tracking-widest text-navy/70 font-bold mb-6">
              <span className="w-2 h-2 rounded-full bg-cobalt inline-block animate-pulse" />
              AUTHENTICATION GATE
            </div>

            <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-navy tracking-tight mb-2">
              Welcome back.
            </h1>
            <p className="font-sans text-sm text-navy/70 mb-8 leading-relaxed">
              Sign in to access your personalized learning history, active knowledge models, and gap reports.
            </p>

            {/* Error Banner */}
            {displayedError && (
              <div
                role="alert"
                className="mb-6 p-4 bg-red-50 border border-red-200 rounded-[8px] text-red-800 text-xs font-sans leading-relaxed space-y-3"
              >
                <div className="flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                  <span className="font-medium">{displayedError}</span>
                </div>
                {(displayedError.includes("Database") ||
                  displayedError.includes("timed out") ||
                  displayedError.includes("port 5433") ||
                  displayedError.includes("reach the backend")) && (
                  <div className="pt-2 border-t border-red-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <span className="text-[11px] text-red-700 font-mono">
                      Database container offline?
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        loginDemoUser(email || "learner@curio.ai");
                        router.replace(returnTo);
                      }}
                      className="px-3 py-1.5 bg-navy text-white text-xs font-mono font-bold rounded-[4px] hover:bg-cobalt transition-colors inline-flex items-center justify-center gap-1.5 shrink-0 shadow-xs"
                    >
                      <span>CONTINUE IN DEMO MODE</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {/* Email Field */}
              <div>
                <label
                  htmlFor="email"
                  className="block font-mono text-xs font-bold uppercase tracking-wider text-navy/80 mb-2"
                >
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-navy/40 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
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
                    className="w-full pl-10 pr-4 py-2.5 bg-ice/40 border border-fog rounded-[6px] font-sans text-sm text-navy placeholder:text-navy/35 focus:outline-none focus:border-cobalt focus:ring-1 focus:ring-cobalt transition-colors"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label
                    htmlFor="password"
                    className="block font-mono text-xs font-bold uppercase tracking-wider text-navy/80"
                  >
                    Password
                  </label>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-navy/40 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
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
                    className="w-full pl-10 pr-11 py-2.5 bg-ice/40 border border-fog rounded-[6px] font-sans text-sm text-navy placeholder:text-navy/35 focus:outline-none focus:border-cobalt focus:ring-1 focus:ring-cobalt transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-navy/40 hover:text-navy p-1 transition-colors"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <KeycapButton
                  variant="navy"
                  size="lg"
                  className="w-full justify-center"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      SIGNING IN...
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      SIGN IN <ArrowRight className="w-4 h-4" />
                    </span>
                  )}
                </KeycapButton>
              </div>

              {/* Instant Demo Access */}
              <div className="pt-3">
                <button
                  type="button"
                  id="demo-login-btn"
                  onClick={() => {
                    loginDemoUser("learner@curio.ai");
                    router.replace(returnTo);
                  }}
                  className="w-full py-2.5 px-4 bg-ice hover:bg-fog/40 border border-fog rounded-[6px] font-mono text-xs font-bold text-navy transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-xs"
                >
                  <Sparkles className="w-3.5 h-3.5 text-gap-orange" />
                  INSTANT DEMO ACCESS (OFFLINE / DEV)
                </button>
              </div>
            </form>

            {/* Bottom Redirect */}
            <div className="mt-8 pt-6 border-t border-fog/60 text-center text-xs font-sans text-navy/70">
              Don&apos;t have an account yet?{" "}
              <Link href="/register" className="font-bold text-cobalt hover:underline">
                Register here
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-sand flex items-center justify-center font-mono text-sm text-navy">Loading...</div>}>
      <LoginForm />
    </React.Suspense>
  );
}

