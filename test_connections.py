"""
Day 1 Smoke Tests
-----------------
All ✅ before moving to Day 2.

Run: python test_connections.py
"""

import os
from dotenv import load_dotenv
load_dotenv()

print("Running Day 1 smoke tests for AI Trading Research Agent...\n")

# ─── Test 1: yfinance ─────────────────────────────────────────────
try:
    import yfinance as yf
    info = yf.Ticker("AAPL").info
    price = info.get("currentPrice")
    print(f"✅ yfinance: AAPL @ ${price}")
except Exception as e:
    print(f"❌ yfinance: {e}")

# ─── Test 2: Ollama (LLM) ─────────────────────────────────────────
try:
    import httpx
    r = httpx.get(f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags", timeout=3)
    models = [m["name"] for m in r.json().get("models", [])]
    target = os.getenv("OLLAMA_MODEL", "mistral")
    if any(m.startswith(target) for m in models):
        print(f"✅ Ollama: '{target}' available")
    else:
        print(f"❌ Ollama: model '{target}' not pulled. Run: ollama pull {target}")
except Exception as e:
    print(f"❌ Ollama: {e} (start with: ollama serve)")

# ─── Test 3: Tavily ───────────────────────────────────────────────
try:
    from tavily import TavilyClient
    tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
    results = tv.search("AAPL stock news")
    print(f"✅ Tavily: {len(results['results'])} news articles")
except Exception as e:
    print(f"❌ Tavily: {e}")

# ─── Test 4: SEC EDGAR ────────────────────────────────────────────
try:
    from sec_edgar_downloader import Downloader
    ua = os.getenv("SEC_USER_AGENT", "Research Agent research@example.com")
    parts = ua.split()
    name, email = " ".join(parts[:-1]), parts[-1]
    dl = Downloader(name, email, "./data/cache/test")
    # Just instantiating tests credentials format
    print(f"✅ SEC EDGAR: ready (UA: {name})")
except Exception as e:
    print(f"❌ SEC EDGAR: {e}")

# ─── Test 5: Reddit (PRAW) ────────────────────────────────────────
try:
    import praw
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        user_agent=os.getenv("REDDIT_USER_AGENT", "test-agent"),
    )
    # Read-only test
    posts = list(reddit.subreddit("wallstreetbets").hot(limit=1))
    print(f"✅ Reddit: connected ({posts[0].title[:40]}...)")
except Exception as e:
    print(f"❌ Reddit: {e}")

# ─── Test 6: Finnhub ──────────────────────────────────────────────
try:
    import finnhub
    fh = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY", ""))
    quote = fh.quote("AAPL")
    print(f"✅ Finnhub: AAPL current price ${quote.get('c')}")
except Exception as e:
    print(f"❌ Finnhub: {e}")

# ─── Test 7: Qdrant ───────────────────────────────────────────────
try:
    from qdrant_client import QdrantClient
    client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
    print(f"✅ Qdrant: connected ({len(client.get_collections().collections)} collections)")
except Exception as e:
    print(f"❌ Qdrant: {e} (start with Docker)")

# ─── Test 8: FinBERT ──────────────────────────────────────────────
try:
    from backend.ml.finbert import score_sentiment
    result = score_sentiment("Apple beat earnings expectations with strong iPhone sales.")
    print(f"✅ FinBERT: '{result['label']}' (score: {result['score']:.3f})")
except Exception as e:
    print(f"❌ FinBERT: {e}")

print("\n✨ Done. Fix any ❌ before Day 2.")
