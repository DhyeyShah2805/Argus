import * as React from "react";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white border border-border rounded-xl shadow-[0_1px_2px_rgba(16,24,40,0.04)] ${className}`}>
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11.5px] font-semibold tracking-[0.04em] uppercase text-muted-foreground mb-3.5">
      {children}
    </div>
  );
}

type Tone = "green" | "red" | "amber" | "blue" | "neutral";
const TONES: Record<Tone, string> = {
  green: "text-[#16a34a] bg-[#f0fdf4] border-[#bbf7d0]",
  red: "text-[#dc2626] bg-[#fef2f2] border-[#fecaca]",
  amber: "text-[#d97706] bg-[#fffbeb] border-[#fde68a]",
  blue: "text-[#2563eb] bg-[#eff6ff] border-[#bfdbfe]",
  neutral: "text-muted-foreground bg-muted border-border",
};

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold rounded-full border px-2.5 py-0.5 leading-snug ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function Progress({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}
