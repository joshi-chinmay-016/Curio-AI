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
          <a
            href="https://github.com/joshi-chinmay-016/Curio-AI"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Curio AI on GitHub"
            className="p-2 text-navy/70 hover:text-navy hover:bg-ice/80 rounded-md transition-colors"
            title="GitHub Repository"
          >
            <svg
              role="img"
              viewBox="0 0 24 24"
              className="w-5 h-5 fill-current"
              xmlns="http://www.w3.org/2000/svg"
            >
              <title>GitHub</title>
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
          </a>
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
