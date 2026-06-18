/* lib/api.ts — typed client + mapper for the Argus FastAPI backend */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── shape the dashboard renders (normalized) ── */
export interface Report {
  ticker: string;
  company: string;
  sector: string;
  price: number | null;
  change1y: number | null;
  mktcap: number | null;
  pe: number | null;
  margin: number | null;
  peerPe: number | null;

  rec: string;
  conf: number;
  horizon: string;

  calibrated: boolean;
  modelRec: string;
  modelConf: number;
  calibNote: string;

  bull: string[];
  bear: string[];

  newsSent: number | null;
  newsPos: number | null;
  newsNeg: number | null;
  newsN: number | null;

  insiderSignal: string;
  insiderSold: number | null;
  insiderBought: number | null;

  riskSeverity: number | null;

  peers: { t: string; pe: number | null; m: number | null }[];
  earnings: { q: string; eps: number | null; est: number | null; s: number | null }[];

  iterations: number;
  reportMarkdown: string;
}

/* ── raw API response (matches FastAPI) ── */
interface RawResponse {
  ticker: string;
  report: string;
  metadata: { company?: string; iterations?: number };
  thesis: {
    bull_case?: string[];
    bear_case?: string[];
    recommendation?: string;
    confidence?: number;
    time_horizon?: string;
    calibration_applied?: boolean;
    calibration_reasoning?: string;
    original_recommendation?: string;
    original_confidence?: number;
  };
  risk_critique: { severity?: number };
  financials: {
    company_name?: string;
    sector?: string;
    current_price?: number;
    price_change_1y_pct?: number;
    market_cap?: number;
    ratios?: Record<string, number>;
  };
  news_summary: { avg_sentiment?: number | null; article_count?: number | null };
  insider_signal?: string | null;
  insider_detail?: {
    shares_bought?: number | null;
    shares_sold?: number | null;
  };
  peers?: { ticker: string; pe_ratio?: number | null; profit_margin?: number | null }[];
  peer_avg_pe?: number | null;
  earnings?: {
    quarter?: string;
    date?: string;
    reported_eps?: number | null;
    estimated_eps?: number | null;
    surprise_pct?: number | null;
  }[];
}

/* normalize the messy backend signal label */
function normalizeInsider(sig?: string | null): string {
  if (!sig) return "neutral";
  if (sig.includes("selling")) return "cluster selling";
  if (sig.includes("buying")) return "cluster buying";
  return "neutral";
}

function map(raw: RawResponse): Report {
  const r = raw.financials?.ratios || {};
  return {
    ticker: raw.ticker,
    company: raw.financials?.company_name || raw.metadata?.company || raw.ticker,
    sector: raw.financials?.sector || "—",
    price: raw.financials?.current_price ?? null,
    change1y: raw.financials?.price_change_1y_pct ?? null,
    mktcap: raw.financials?.market_cap ?? null,
    pe: r["P/E (trailing)"] ?? null,
    margin: r["Profit Margin"] ?? null,
    peerPe: raw.peer_avg_pe ?? null,

    rec: raw.thesis?.recommendation || "HOLD",
    conf: raw.thesis?.confidence ?? 0,
    horizon: raw.thesis?.time_horizon || "medium",

    calibrated: !!raw.thesis?.calibration_applied,
    modelRec: raw.thesis?.original_recommendation || raw.thesis?.recommendation || "HOLD",
    modelConf: raw.thesis?.original_confidence ?? raw.thesis?.confidence ?? 0,
    calibNote: raw.thesis?.calibration_reasoning || "",

    bull: raw.thesis?.bull_case || [],
    bear: raw.thesis?.bear_case || [],

    newsSent: raw.news_summary?.avg_sentiment ?? null,
    newsPos: null,
    newsNeg: null,
    newsN: raw.news_summary?.article_count ?? null,

    insiderSignal: normalizeInsider(raw.insider_signal),
    insiderSold: raw.insider_detail?.shares_sold ?? null,
    insiderBought: raw.insider_detail?.shares_bought ?? null,

    riskSeverity: raw.risk_critique?.severity ?? null,

    peers: (raw.peers || []).map((p) => ({
      t: p.ticker,
      pe: p.pe_ratio ?? null,
      m: p.profit_margin ?? null,
    })),
    earnings: (raw.earnings || []).map((e) => ({
      q: e.quarter || e.date || "—",
      eps: e.reported_eps ?? null,
      est: e.estimated_eps ?? null,
      s: e.surprise_pct ?? null,
    })),

    iterations: raw.metadata?.iterations ?? 1,
    reportMarkdown: raw.report || "",
  };
}

export async function research(ticker: string): Promise<Report> {
  const res = await fetch(`${API_URL}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Research failed (${res.status}). ${txt.slice(0, 200)}`);
  }
  return map(await res.json());
}
