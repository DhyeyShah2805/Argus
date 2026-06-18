"use client";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export function PriceChart({ seed, price, up }: { seed: number; price: number; up: boolean }) {
  const data: { d: number; p: number }[] = [];
  let v = price * 0.82;
  let s = seed * 9301;
  for (let i = 0; i < 60; i++) {
    s = (s * 9301 + 49297) % 233280;
    v += (s / 233280 - 0.45) * price * 0.025;
    v = Math.max(price * 0.6, Math.min(price * 1.15, v));
    data.push({ d: i, p: +v.toFixed(2) });
  }
  data[data.length - 1].p = price;
  const c = up ? "#16a34a" : "#dc2626";

  return (
    <ResponsiveContainer width="100%" height={158}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
        <defs>
          <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={c} stopOpacity={0.18} />
            <stop offset="100%" stopColor={c} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#f4f4f5" vertical={false} />
        <XAxis dataKey="d" hide />
        <YAxis domain={["dataMin", "dataMax"]} hide />
        <Tooltip
          contentStyle={{ background: "#fff", border: "1px solid #e4e4e7", borderRadius: 8, fontSize: 12, boxShadow: "0 4px 12px rgba(16,24,40,.08)" }}
          labelStyle={{ display: "none" }}
          formatter={(val: number) => [`$${val}`, ""]}
        />
        <Area type="monotone" dataKey="p" stroke={c} strokeWidth={1.8} fill="url(#ga)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
