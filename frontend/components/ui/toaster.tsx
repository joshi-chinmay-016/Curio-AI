"use client";

import { useToast } from "@/hooks/use-toast";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  if (!toasts.length) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        const isDestructive = toast.variant === "destructive";

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 bg-white text-navy border-2 border-navy shadow-[4px_4px_0_0_#0F2B4A] transition-all animate-in fade-in slide-in-from-bottom-2 ${
              isDestructive
                ? "border-t-[3px] border-t-gap-orange"
                : "border-t-[3px] border-t-cobalt"
            }`}
          >
            {isDestructive ? (
              <AlertTriangle className="h-4 w-4 text-gap-orange shrink-0 mt-0.5" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-cobalt shrink-0 mt-0.5" />
            )}
            <div className="flex-1 min-w-0">
              {toast.title && (
                <p className="font-mono text-xs font-bold uppercase tracking-wider text-navy leading-snug">
                  {toast.title}
                </p>
              )}
              {toast.description && (
                <p className="font-sans text-xs text-navy/80 mt-1 leading-normal">
                  {toast.description}
                </p>
              )}
            </div>
            <button
              onClick={() => dismiss(toast.id)}
              className="text-navy/50 hover:text-navy transition-colors shrink-0 p-0.5"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
