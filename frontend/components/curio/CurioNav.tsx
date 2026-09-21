"use client";

import React from "react";
import Link from "next/link";
import { KeycapButton } from "@/components/curio/KeycapButton";

export function CurioNav() {
  return (
    <header className="w-full bg-white/90 backdrop-blur-[2px] border-b border-fog sticky top-0 z-40 px-6 py-3.5">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="font-mono text-xl font-bold tracking-wider text-navy hover:text-cobalt transition-colors"
          >
            CURIO<span className="text-gap-orange">.</span>
          </Link>

          <nav className="hidden md:flex items-center gap-4 text-xs font-mono font-semibold uppercase">
            <Link
              href="/topics"
              className="text-navy/70 hover:text-navy transition-colors px-2 py-1"
            >
              TOPICS
            </Link>
            <Link
              href="/history"
              className="text-navy/70 hover:text-navy transition-colors px-2 py-1"
            >
              HISTORY
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/topics">
            <KeycapButton variant="ghost" size="sm">
              SIGN IN
            </KeycapButton>
          </Link>
          <Link href="/topics">
            <KeycapButton variant="navy" size="sm">
              GET STARTED →
            </KeycapButton>
          </Link>
        </div>
      </div>
    </header>
  );
}
