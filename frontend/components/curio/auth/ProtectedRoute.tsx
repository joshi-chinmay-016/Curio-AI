"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, initAuth } = useAuthStore();

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const returnTo = encodeURIComponent(pathname || "/dashboard");
      router.replace(`/login?returnTo=${returnTo}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-ice flex flex-col items-center justify-center p-6 text-navy">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-cobalt border-t-transparent rounded-full animate-spin" />
          <p className="font-mono text-xs uppercase tracking-widest text-navy/60 font-semibold animate-pulse">
            AUTHENTICATING SESSION...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
