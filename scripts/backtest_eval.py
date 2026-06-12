"""
Backtest Evaluation Framework
-----------------------------
Runs the agent on 20 tickers across 4 sectors,
compares each recommendation against actual 30-day forward returns,
and produces a structured accuracy report.

Run: python -m scripts.backtest_eval
"""

import asyncio
import json
import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import yfinance as yf
from backend.agents.graph import run_research

logging.basicConfig(level=logging.WARNING)   # quiet sub-agent noise
logger = logging.getLogger("backtest")
logger.setLevel(logging.INFO)


# ─── Test Universe ───────────────────────────────────────────────
TEST_UNIVERSE = {
    "Tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Finance": ["JPM", "BAC", "GS", "WFC", "MS"],
    "Healthcare": ["JNJ", "PFE", "UNH", "ABBV", "MRK"],
    "Consumer": ["AMZN", "TSLA", "WMT", "KO", "NKE"],
}


# ─── JSON helper (numpy-safe) ────────────────────────────────────

def _to_jsonable(obj):
    """Convert numpy types to native Python so json.dumps works."""
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


# ─── Scoring Logic ───────────────────────────────────────────────

def actual_30d_return(ticker: str) -> float:
    """Return 30-day forward return %, or None if data is missing."""
    try:
        hist = yf.Ticker(ticker).history(period="60d")
        if len(hist) < 30:
            return None
        return ((hist["Close"].iloc[-1] / hist["Close"].iloc[-30]) - 1) * 100
    except Exception as e:
        logger.warning(f"Failed to fetch return for {ticker}: {e}")
        return None


def score_alignment(recommendation: str, actual_return: float):
    """Was the recommendation directionally correct? Returns native Python bool."""
    if actual_return is None:
        return None
    rec = (recommendation or "").upper()
    if rec == "BUY":
        return bool(actual_return > 0)
    elif rec == "SELL":
        return bool(actual_return < 0)
    elif rec == "HOLD":
        return bool(abs(actual_return) < 5)
    return None


def confidence_band(conf: int) -> str:
    """Bucket confidence into low/medium/high."""
    if conf is None:
        return "unknown"
    if conf < 60:
        return "low (<60)"
    if conf < 75:
        return "medium (60-74)"
    return "high (75+)"


# ─── Main Backtest Loop ──────────────────────────────────────────

async def run_backtest():
    results = []
    total = sum(len(tickers) for tickers in TEST_UNIVERSE.values())
    counter = 0

    print(f"\n{'='*60}")
    print(f"BACKTEST — {total} tickers across {len(TEST_UNIVERSE)} sectors")
    print(f"{'='*60}\n")

    for sector, tickers in TEST_UNIVERSE.items():
        print(f"\n── Sector: {sector} ────────────────")
        for ticker in tickers:
            counter += 1
            print(f"[{counter}/{total}] {ticker}... ", end="", flush=True)

            try:
                state = await run_research(ticker)
                thesis = state.get("thesis", {})
                rec = thesis.get("recommendation", "—")
                conf = thesis.get("confidence", 0) or 0
                actual = actual_30d_return(ticker)
                aligned = score_alignment(rec, actual)

                results.append({
                    "sector": sector,
                    "ticker": ticker,
                    "recommendation": rec,
                    "confidence": int(conf) if conf else 0,
                    "actual_30d_return_pct": round(float(actual), 2) if actual is not None else None,
                    "aligned": aligned,
                    "iterations": state.get("iteration", 0),
                })

                status = "✓" if aligned else ("✗" if aligned is False else "?")
                actual_str = f"{actual:+.2f}%" if actual is not None else "N/A"
                print(f"{rec} ({conf}%) | actual {actual_str} | {status}")

            except Exception as e:
                logger.error(f"  Failed: {e}")
                results.append({
                    "sector": sector,
                    "ticker": ticker,
                    "error": str(e),
                })
                print(f"FAILED ({e})")

    return results


# ─── Reporting ───────────────────────────────────────────────────

def compute_metrics(results: list) -> dict:
    """Compute overall + per-sector + per-confidence metrics."""
    valid = [r for r in results if r.get("aligned") is not None]
    if not valid:
        return {"error": "no valid results"}

    overall_acc = sum(1 for r in valid if r["aligned"]) / len(valid) * 100

    # Per-sector
    sector_metrics = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in valid:
        sector_metrics[r["sector"]]["total"] += 1
        if r["aligned"]:
            sector_metrics[r["sector"]]["correct"] += 1

    sector_acc = {
        sector: {
            "accuracy_pct": round(m["correct"] / m["total"] * 100, 1),
            "n": m["total"],
        }
        for sector, m in sector_metrics.items()
    }

    # Per-confidence band
    conf_metrics = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in valid:
        band = confidence_band(r["confidence"])
        conf_metrics[band]["total"] += 1
        if r["aligned"]:
            conf_metrics[band]["correct"] += 1

    conf_acc = {
        band: {
            "accuracy_pct": round(m["correct"] / m["total"] * 100, 1),
            "n": m["total"],
        }
        for band, m in conf_metrics.items()
    }

    # Distribution of recommendations
    rec_dist = defaultdict(int)
    for r in valid:
        rec_dist[r["recommendation"]] += 1

    return {
        "total_tickers": len(results),
        "tickers_scored": len(valid),
        "overall_accuracy_pct": round(overall_acc, 1),
        "by_sector": sector_acc,
        "by_confidence": conf_acc,
        "recommendation_distribution": dict(rec_dist),
    }


def write_csv(results: list, path: Path):
    keys = ["sector", "ticker", "recommendation", "confidence",
            "actual_30d_return_pct", "aligned", "iterations"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            if "error" not in r:
                writer.writerow(r)


def write_markdown(metrics: dict, results: list, path: Path):
    lines = [
        "# Backtest Results",
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## Headline",
        "",
        f"**Overall directional accuracy: {metrics['overall_accuracy_pct']}%** "
        f"({metrics['tickers_scored']}/{metrics['total_tickers']} tickers scored)",
        "",
        "## Accuracy by Sector",
        "",
        "| Sector | Accuracy | N |",
        "|--------|----------|---|",
    ]
    for sector, m in metrics["by_sector"].items():
        lines.append(f"| {sector} | {m['accuracy_pct']}% | {m['n']} |")

    lines += [
        "",
        "## Accuracy by Confidence Band",
        "",
        "| Confidence | Accuracy | N |",
        "|------------|----------|---|",
    ]
    for band, m in metrics["by_confidence"].items():
        lines.append(f"| {band} | {m['accuracy_pct']}% | {m['n']} |")

    lines += [
        "",
        "## Recommendation Distribution",
        "",
        "| Recommendation | Count |",
        "|----------------|-------|",
    ]
    for rec, count in metrics["recommendation_distribution"].items():
        lines.append(f"| {rec} | {count} |")

    lines += [
        "",
        "## Per-Ticker Details",
        "",
        "| Sector | Ticker | Rec | Conf | Actual 30d | Aligned |",
        "|--------|--------|-----|------|-----------|---------|",
    ]
    for r in results:
        if "error" in r:
            continue
        symbol = "✓" if r["aligned"] else ("✗" if r["aligned"] is False else "?")
        ret = r.get("actual_30d_return_pct")
        ret_str = f"{ret:+.2f}%" if ret is not None else "N/A"
        lines.append(
            f"| {r['sector']} | {r['ticker']} | {r['recommendation']} | "
            f"{r['confidence']}% | {ret_str} | {symbol} |"
        )

    path.write_text("\n".join(lines))


# ─── Entrypoint ──────────────────────────────────────────────────

if __name__ == "__main__":
    output_dir = Path("./data/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = asyncio.run(run_backtest())
    metrics = compute_metrics(results)

    (output_dir / "backtest_results.json").write_text(
        json.dumps(results, indent=2, default=_to_jsonable)
    )
    (output_dir / "backtest_metrics.json").write_text(
        json.dumps(metrics, indent=2, default=_to_jsonable)
    )
    write_csv(results, output_dir / "backtest_results.csv")
    write_markdown(metrics, results, output_dir / "BACKTEST_RESULTS.md")

    print(f"\n{'='*60}")
    print(f"OVERALL ACCURACY: {metrics['overall_accuracy_pct']}%")
    print(f"({metrics['tickers_scored']} of {metrics['total_tickers']} tickers scored)")
    print(f"{'='*60}")
    print(f"\nBy sector:")
    for sector, m in metrics["by_sector"].items():
        print(f"  {sector:12s} {m['accuracy_pct']:5.1f}%  (n={m['n']})")
    print(f"\nRecommendation distribution:")
    for rec, count in metrics["recommendation_distribution"].items():
        print(f"  {rec:6s} {count}")
    print(f"\nResults saved to:")
    print(f"  → data/reports/backtest_results.csv")
    print(f"  → data/reports/backtest_metrics.json")
    print(f"  → data/reports/BACKTEST_RESULTS.md")