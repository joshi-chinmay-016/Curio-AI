"use client";

import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "info";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  description?: string;
  duration?: number;
}

type ToastListener = (toasts: ToastItem[]) => void;

let toasts: ToastItem[] = [];
const listeners: Set<ToastListener> = new Set();

function notify() {
  listeners.forEach((listener) => listener([...toasts]));
}

export const curioToast = {
  success: (message: string, description?: string, duration = 4000) => {
    const id = "toast_" + Date.now() + "_" + Math.random().toString(36).substring(2, 6);
    toasts = [...toasts, { id, type: "success", message: message.toUpperCase(), description, duration }];
    notify();
  },
  error: (message: string, description?: string, duration = 5000) => {
    const id = "toast_" + Date.now() + "_" + Math.random().toString(36).substring(2, 6);
    toasts = [...toasts, { id, type: "error", message: message.toUpperCase(), description, duration }];
    notify();
  },
  info: (message: string, description?: string, duration = 4000) => {
    const id = "toast_" + Date.now() + "_" + Math.random().toString(36).substring(2, 6);
    toasts = [...toasts, { id, type: "info", message: message.toUpperCase(), description, duration }];
    notify();
  },
  dismiss: (id: string) => {
    toasts = toasts.filter((t) => t.id !== id);
    notify();
  },
};

export function CurioToaster() {
  const [activeToasts, setActiveToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    const listener: ToastListener = (updated) => setActiveToasts(updated);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return (
    <div
      aria-live="assertive"
      className="fixed bottom-6 right-6 z-[10000] flex flex-col gap-3 max-w-sm w-full pointer-events-none"
    >
      <AnimatePresence>
        {activeToasts.map((toast) => (
          <ToastCard key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastCard({ toast }: { toast: ToastItem }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      curioToast.dismiss(toast.id);
    }, toast.duration || 4000);

    return () => clearTimeout(timer);
  }, [toast]);

  const topStripeClass =
    toast.type === "success"
      ? "border-t-[3px] border-t-cobalt"
      : toast.type === "error"
      ? "border-t-[3px] border-t-gap-orange"
      : "border-t-[3px] border-t-navy";

  const Icon =
    toast.type === "success"
      ? CheckCircle2
      : toast.type === "error"
      ? AlertTriangle
      : Info;

  const iconColor =
    toast.type === "success"
      ? "text-cobalt"
      : toast.type === "error"
      ? "text-gap-orange"
      : "text-navy";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.95 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      role="alert"
      className={`pointer-events-auto bg-white border-2 border-navy rounded-none shadow-[4px_4px_0_0_#0F2B4A] p-4 text-navy ${topStripeClass}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${iconColor}`} />
          <div>
            <div className="font-mono text-xs font-semibold tracking-wider text-navy">
              {toast.message}
            </div>
            {toast.description && (
              <div className="font-sans text-xs text-navy/75 mt-1">
                {toast.description}
              </div>
            )}
          </div>
        </div>
        <button
          onClick={() => curioToast.dismiss(toast.id)}
          className="text-navy/50 hover:text-navy transition-colors shrink-0 p-0.5"
          aria-label="Dismiss notification"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </motion.div>
  );
}
