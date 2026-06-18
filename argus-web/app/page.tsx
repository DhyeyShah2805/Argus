"use client";

import { useState } from "react";
import {
  Search, FileText, BarChart3, Newspaper, CalendarClock, UserMinus, Building2,
  ArrowRight, TrendingUp, TrendingDown, Minus, Check, Github, Eye, Loader2,
} from "lucide-react";
import { Card, Eyebrow, Badge, Progress } from "@/components/ui/primitives";
import { PriceChart } from "@/components/argus/PriceChart";
import { research, type Report } from "@/lib/api";

const AGENTS = [
  { label: "Filings", icon: FileText, src: "SEC EDGAR" },
  { label: "Financials", icon: BarChart3, src: "yfinance" },
  { label: "News", icon: Newspaper, src: "Tavily + FinBERT" },
  { label: "Earnings", icon: CalendarClock, src: "yfinance" },
  { label: "Insider", icon: UserMinus, src: "Finnhub" },
  { label: "Peers", icon: Building2, src: "Finnhub" },
];

const fmtCap = (n: number | null) =>
  n == null ? "—" : n >= 1e12 ? "$" + (n / 1e12).toFixed(2) + "T" : "$" + (n / 1e9).toFixed(0) + "B";

const recTone = (r: string): "green" | "red" | "amber" =>
  r === "BUY" ? "green" : r === "SELL" ? "red" : "amber";
const recColor = (r: string) => (r === "BUY" ? "#16a34a" : r === "SELL" ? "#dc2626" : "#d97706");
const RecIcon = ({ r, size = 15 }: { r: string; size?: number }) =>
  r === "BUY" ? <TrendingUp size={size} /> : r === "SELL" ? <TrendingDown size={size} /> : <Minus size={size} />;

export default function Home() {
  const [input, setInput] = useState("AAPL");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(sym?: string) {
    const ticker = (sym || input).toUpperCase().trim();
    if (!ticker) return;
    setLoading(true);
    setError(null);
    try {
      setReport(await research(ticker));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const r = report;
  const up = (r?.change1y ?? 0) >= 0;
  const seed = r ? r.ticker.split("").reduce((a, c) => a + c.charCodeAt(0), 0) : 7;
  const valRatio = r && r.pe && r.peerPe ? r.pe / r.peerPe : null;

  const signals = r
    ? [
        {
          k: "News Sentiment",
          v: r.newsSent == null ? "—" : (r.newsSent > 0 ? "+" : "") + r.newsSent.toFixed(2),
          sub: r.newsN ? `${r.newsN} articles` : "no data",
          pct: r.newsSent == null ? 0 : Math.round(((r.newsSent + 1) / 2) * 100),
          color: r.newsSent == null ? "#71717a" : r.newsSent > 0.05 ? "#16a34a" : r.newsSent < -0.05 ? "#dc2626" : "#d97706",
        },
        {
          k: "Insider (90d)",
          v: r.insiderSignal === "cluster selling" ? "Net Sell" : r.insiderSignal === "cluster buying" ? "Net Buy" : "Neutral",
          sub:
            r.insiderSold != null
              ? `${(r.insiderSold / 1000).toFixed(0)}k sold · ${((r.insiderBought ?? 0) / 1000).toFixed(0)}k bought`
              : "—",
          pct: r.insiderSignal === "cluster selling" ? 78 : r.insiderSignal === "cluster buying" ? 70 : 45,
          color: r.insiderSignal === "cluster selling" ? "#dc2626" : r.insiderSignal === "cluster buying" ? "#16a34a" : "#71717a",
        },
        {
          k: "Risk Severity",
          v: r.riskSeverity == null ? "—" : `${r.riskSeverity}/10`,
          sub: (r.riskSeverity ?? 0) >= 7 ? "Elevated" : (r.riskSeverity ?? 0) >= 5 ? "Moderate" : "Contained",
          pct: (r.riskSeverity ?? 0) * 10,
          color: (r.riskSeverity ?? 0) >= 7 ? "#dc2626" : (r.riskSeverity ?? 0) >= 5 ? "#d97706" : "#16a34a",
        },
        {
          k: "Valuation vs Peers",
          v: valRatio == null ? "—" : `${valRatio.toFixed(1)}×`,
          sub: r.pe && r.peerPe ? `P/E ${r.pe.toFixed(1)} vs ${r.peerPe.toFixed(1)} avg` : "—",
          pct: valRatio == null ? 0 : Math.min(100, (valRatio / 4) * 100),
          color: valRatio == null ? "#71717a" : valRatio > 1.5 ? "#dc2626" : valRatio < 0.9 ? "#16a34a" : "#d97706",
        },
      ]
    : [];

  return (
    <div className="min-h-screen bg-[#fafafa] text-foreground font-sans">
      {/* nav */}
      <nav className="sticky top-0 z-10 bg-white border-b border-border h-[58px] px-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-primary grid place-items-center">
            <Eye size={16} className="text-primary-foreground" />
          </div>
          <span className="font-semibold text-[15.5px] tracking-tight">Argus</span>
          <span className="text-[12.5px] text-muted-foreground ml-0.5 pl-2.5 border-l border-border">Equity Research</span>
        </div>
        <a
          href="https://github.com/DhyeyShah2805"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium border border-border rounded-lg px-3 py-1.5 hover:bg-muted transition-colors"
        >
          <Github size={15} /> GitHub
        </a>
      </nav>

      <div className="max-w-[1080px] mx-auto px-6 pt-8 pb-16">
        {/* hero / search */}
        <div className="mb-7">
          <Eyebrow>Multi-agent equity research</Eyebrow>
          <h1 className="m-0 mb-4 text-[30px] font-semibold tracking-tight leading-[1.15]">
            Research any stock in one query.
          </h1>
          <div className="flex gap-2.5 flex-wrap max-w-[540px]">
            <div className="relative flex-1 min-w-[220px]">
              <Search size={16} className="text-muted-foreground absolute left-3.5 top-3" />
              <input
                value={input}
                onChange={(e) => setInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && run()}
                placeholder="Enter a ticker (e.g. AAPL)"
                className="w-full bg-white border border-border rounded-[9px] py-2.5 pl-9 pr-3 text-sm outline-none focus:border-muted-foreground/40"
              />
            </div>
            <button
              onClick={() => run()}
              disabled={loading}
              className="inline-flex items-center gap-2 text-sm font-semibold text-primary-foreground bg-primary rounded-[9px] px-5 py-2.5 hover:bg-[#27272a] transition-colors disabled:opacity-60"
            >
              {loading && <Loader2 size={15} className="animate-spin" />}
              {loading ? "Researching…" : "Research"}
            </button>
          </div>
          <div className="flex gap-1.5 mt-3 items-center flex-wrap">
            <span className="text-xs text-muted-foreground">Samples</span>
            {["AAPL", "TSLA", "JNJ", "NVDA", "JPM"].map((k) => (
              <button
                key={k}
                onClick={() => { setInput(k); run(k); }}
                className="font-mono text-xs font-medium border border-border rounded-md px-2.5 py-1 hover:bg-muted transition-colors"
              >
                {k}
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            First run on a ticker takes ~60–90s (six agents query live sources, then synthesis → calibrate → risk).
          </p>
        </div>

        {error && (
          <Card className="p-4 mb-5 border-[#fecaca] bg-[#fef2f2]">
            <span className="text-sm text-[#dc2626]">{error}</span>
          </Card>
        )}

        {/* empty state */}
        {!r && !loading && (
          <Card className="p-12 text-center">
            <div className="w-12 h-12 rounded-xl bg-muted grid place-items-center mx-auto mb-4">
              <Eye size={22} className="text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground m-0">Enter a ticker above to generate a research report.</p>
          </Card>
        )}

        {/* loading state */}
        {loading && !r && (
          <Card className="p-12 text-center">
            <Loader2 size={28} className="animate-spin text-muted-foreground mx-auto mb-4" />
            <p className="text-sm text-muted-foreground m-0">Six agents are gathering data in parallel…</p>
          </Card>
        )}

        {r && (
          <>
            {/* pipeline */}
            <Card className="p-5 mb-[18px]">
              <div className="flex justify-between items-center mb-4">
                <Eyebrow>Pipeline · 6 agents, parallel</Eyebrow>
                <span className="text-xs font-semibold text-[#16a34a]">Complete · {r.iterations} iteration{r.iterations > 1 ? "s" : ""}</span>
              </div>
              <div className="grid gap-2.5" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
                {AGENTS.map((a) => (
                  <div key={a.label} className="flex items-center gap-2.5 px-3 py-2.5 rounded-[9px] border border-border bg-white">
                    <div className="w-[30px] h-[30px] rounded-md bg-[#f0fdf4] grid place-items-center shrink-0">
                      <Check size={15} className="text-[#16a34a]" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[13px] font-medium">{a.label}</div>
                      <div className="text-[11px] text-muted-foreground truncate">{a.src}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* verdict + chart */}
            <div className="grid gap-[18px] mb-[18px]" style={{ gridTemplateColumns: "minmax(280px, 1fr) minmax(0, 1.4fr)" }}>
              <Card className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-mono text-lg font-semibold">{r.ticker}</div>
                    <div className="text-[13px] text-muted-foreground mt-0.5">{r.company}</div>
                  </div>
                  <Badge tone="neutral">{r.sector}</Badge>
                </div>

                <div className="mt-[22px] flex items-center gap-3">
                  <Badge tone={recTone(r.rec)}><RecIcon r={r.rec} /> {r.rec}</Badge>
                  <span className="font-mono text-sm text-muted-foreground">{r.conf}% confidence · {r.horizon}-term</span>
                </div>
                <div className="mt-3.5"><Progress pct={r.conf} color={recColor(r.rec)} /></div>

                <div className="mt-[22px] p-4 bg-[#fafafa] border border-border rounded-[10px]">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-[11.5px] font-semibold tracking-[0.04em] uppercase text-muted-foreground">Calibration Layer</span>
                    <Badge tone={r.calibrated ? "blue" : "green"}>{r.calibrated ? "Adjusted" : "Kept"}</Badge>
                  </div>
                  <div className="flex items-center gap-2.5 font-mono text-[13px]">
                    <span className="text-muted-foreground">{r.modelRec} {r.modelConf}%</span>
                    <ArrowRight size={14} className={r.calibrated ? "text-[#2563eb]" : "text-muted-foreground"} />
                    <span className={`font-semibold ${r.calibrated ? "text-[#2563eb]" : "text-[#16a34a]"}`}>{r.rec} {r.conf}%</span>
                  </div>
                  {r.calibNote && <p className="mt-2.5 mb-0 text-[12.5px] leading-[1.55] text-muted-foreground">{r.calibNote}</p>}
                </div>
              </Card>

              <Card className="p-[22px]">
                <div className="flex justify-between items-baseline mb-1.5">
                  <Eyebrow>Price · 1Y</Eyebrow>
                  <div className="font-mono text-sm">
                    <span className="font-semibold">${r.price?.toFixed(2) ?? "—"}</span>
                    {r.change1y != null && (
                      <span className={`ml-2.5 text-[13px] ${up ? "text-[#16a34a]" : "text-[#dc2626]"}`}>
                        {up ? "▲" : "▼"} {Math.abs(r.change1y)}%
                      </span>
                    )}
                  </div>
                </div>
                <PriceChart seed={seed} price={r.price ?? 100} up={up} />
                <div className="flex border-t border-border mt-3 pt-3.5">
                  {[
                    ["Market Cap", fmtCap(r.mktcap)],
                    ["P/E", r.pe?.toFixed(1) ?? "—"],
                    ["Margin", r.margin != null ? (r.margin * 100).toFixed(1) + "%" : "—"],
                    ["Conf", `${r.conf}%`],
                  ].map(([k, v], i) => (
                    <div key={i} className={`flex-1 ${i < 3 ? "border-r border-border" : ""} ${i ? "pl-3.5" : ""}`}>
                      <div className="text-[11px] text-muted-foreground">{k}</div>
                      <div className="font-mono text-sm font-medium mt-0.5">{v}</div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* signals */}
            <div className="grid gap-3.5 mb-[18px]" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
              {signals.map((s, i) => (
                <Card key={i} className="p-[18px]">
                  <div className="text-[12.5px] text-muted-foreground font-medium">{s.k}</div>
                  <div className="font-mono text-[22px] font-semibold my-2" style={{ color: s.color }}>{s.v}</div>
                  <div className="text-[11.5px] text-muted-foreground mb-3">{s.sub}</div>
                  <Progress pct={s.pct} color={s.color} />
                </Card>
              ))}
            </div>

            {/* bull / bear */}
            <div className="grid grid-cols-2 gap-[18px] mb-[18px]">
              {[
                { t: "Bull Case", arr: r.bull, tone: "green" as const, color: "#16a34a", bg: "#f0fdf4", bd: "#bbf7d0", ic: <TrendingUp size={15} /> },
                { t: "Bear Case", arr: r.bear, tone: "red" as const, color: "#dc2626", bg: "#fef2f2", bd: "#fecaca", ic: <TrendingDown size={15} /> },
              ].map((side) => (
                <Card key={side.t} className="p-[22px]">
                  <div className="inline-flex items-center gap-1.5 font-semibold text-sm mb-4" style={{ color: side.color }}>
                    {side.ic} {side.t}
                  </div>
                  <div className="flex flex-col gap-3">
                    {side.arr.map((b, i) => (
                      <div key={i} className="flex gap-2.5">
                        <span
                          className="w-5 h-5 rounded-md text-[11px] font-semibold grid place-items-center shrink-0 font-mono border"
                          style={{ background: side.bg, borderColor: side.bd, color: side.color }}
                        >
                          {i + 1}
                        </span>
                        <span className="text-[13.5px] leading-[1.55] text-[#3f3f46]">{b}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>

            {/* earnings + peers */}
            <div className="grid grid-cols-2 gap-[18px]">
              <Card className="p-[22px]">
                <Eyebrow>Recent Earnings</Eyebrow>
                <table className="w-full border-collapse font-mono text-[13px]">
                  <thead>
                    <tr className="text-muted-foreground text-[11px]">
                      <th className="text-left pb-2 font-medium">QTR</th>
                      <th className="text-right font-medium">EPS</th>
                      <th className="text-right font-medium">EST</th>
                      <th className="text-right font-medium">SURPRISE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.earnings.map((e, i) => (
                      <tr key={i} className="border-t border-border">
                        <td className="py-2.5">{e.q}</td>
                        <td className="text-right">{e.eps?.toFixed(2) ?? "—"}</td>
                        <td className="text-right text-muted-foreground">{e.est?.toFixed(2) ?? "—"}</td>
                        <td className="text-right font-semibold" style={{ color: (e.s ?? 0) >= 0 ? "#16a34a" : "#dc2626" }}>
                          {e.s == null ? "—" : (e.s >= 0 ? "+" : "") + e.s.toFixed(1) + "%"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>

              <Card className="p-[22px]">
                <Eyebrow>Competitive Positioning</Eyebrow>
                <table className="w-full border-collapse font-mono text-[13px]">
                  <thead>
                    <tr className="text-muted-foreground text-[11px]">
                      <th className="text-left pb-2 font-medium">TICKER</th>
                      <th className="text-right font-medium">P/E</th>
                      <th className="text-right font-medium">MARGIN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.peers.map((p, i) => {
                      const self = p.t === r.ticker;
                      return (
                        <tr key={i} className={`border-t border-border ${self ? "bg-muted" : ""}`}>
                          <td className={`py-2.5 px-2 ${self ? "font-semibold" : ""}`}>
                            {p.t}{self && <span className="ml-1.5 text-[10px] text-muted-foreground font-sans">subject</span>}
                          </td>
                          <td className="text-right">{p.pe?.toFixed(1) ?? "—"}</td>
                          <td className="text-right text-muted-foreground">{p.m != null ? (p.m * 100).toFixed(1) + "%" : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </Card>
            </div>

            {/* footer */}
            <div className="mt-7 pt-[18px] border-t border-border flex justify-between flex-wrap gap-2">
              <span className="text-xs text-muted-foreground">SEC EDGAR · yfinance · Finnhub · Tavily · FinBERT</span>
              <span className="text-xs text-muted-foreground">Educational research · not investment advice</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
