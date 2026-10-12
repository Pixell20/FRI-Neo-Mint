"""Market data service.

Uses a deterministic-ish simulated feed (seeded random walk per symbol per time
bucket) so the sandbox works offline and is reproducible. Quotes are cached in
Redis (falls back to an in-process dict if Redis is unreachable) so repeated
requests inside `quote_cache_seconds` never recompute or hit an upstream API.
"""
import hashlib
import json
import math
import random
import time

import redis

from ..config import get_settings

settings = get_settings()

# symbol -> (company name, base price)
UNIVERSE: dict[str, tuple[str, float]] = {
    "AAPL": ("Apple Inc.", 228.0),
    "MSFT": ("Microsoft Corp.", 445.0),
    "GOOGL": ("Alphabet Inc.", 182.0),
    "AMZN": ("Amazon.com Inc.", 205.0),
    "NVDA": ("NVIDIA Corp.", 138.0),
    "TSLA": ("Tesla Inc.", 255.0),
    "META": ("Meta Platforms", 590.0),
    "JPM": ("JPMorgan Chase", 232.0),
    "V": ("Visa Inc.", 305.0),
    "KO": ("Coca-Cola Co.", 68.0),
    "DIS": ("Walt Disney Co.", 96.0),
    "NFLX": ("Netflix Inc.", 720.0),
    "XOM": ("Exxon Mobil", 118.0),
    "PFE": ("Pfizer Inc.", 28.0),
    "INFY": ("Infosys Ltd.", 21.0),
}

_local_cache: dict[str, tuple[float, str]] = {}
_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    global _redis
    if _redis is None:
        try:
            client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.3, decode_responses=True)
            client.ping()
            _redis = client
        except Exception:
            return None
    return _redis


def _cache_get(key: str) -> str | None:
    r = _get_redis()
    if r is not None:
        try:
            return r.get(key)
        except Exception:
            pass
    hit = _local_cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def _cache_set(key: str, value: str, ttl: int) -> None:
    r = _get_redis()
    if r is not None:
        try:
            r.setex(key, ttl, value)
            return
        except Exception:
            pass
    _local_cache[key] = (time.time() + ttl, value)


def _price_at(symbol: str, bucket: int) -> float:
    """Random-walk price: sum of seeded daily-ish shocks up to `bucket`."""
    base = UNIVERSE[symbol][1]
    seed = int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % 10_000
    rng = random.Random(seed)
    # slow drift curve plus a bucket-level shock
    drift = 0.03 * math.sin(bucket / 5000.0 + seed)
    shock = random.Random(f"{symbol}:{bucket}").gauss(0, 0.004)
    _ = rng  # reserved for future per-symbol volatility
    return max(0.5, base * (1 + drift + shock))


def get_quote(symbol: str) -> dict | None:
    symbol = symbol.upper().strip()
    if symbol not in UNIVERSE:
        return None
    key = f"quote:{symbol}"
    cached = _cache_get(key)
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return data

    ttl = settings.quote_cache_seconds
    bucket = int(time.time() // ttl)
    price = _price_at(symbol, bucket)
    day_bucket = int(time.time() // 86_400) * (86_400 // ttl)
    prev_close = _price_at(symbol, day_bucket)
    samples = [_price_at(symbol, b) for b in range(day_bucket, bucket + 1, max(1, (bucket - day_bucket) // 20 or 1))]
    samples.append(price)
    data = {
        "symbol": symbol,
        "name": UNIVERSE[symbol][0],
        "price": round(price, 2),
        "change": round(price - prev_close, 2),
        "change_pct": round((price - prev_close) / prev_close * 100, 2),
        "day_high": round(max(samples), 2),
        "day_low": round(min(samples), 2),
        "cached": False,
    }
    _cache_set(key, json.dumps(data), ttl)
    return data


def list_stocks() -> list[dict]:
    return [q for s in UNIVERSE if (q := get_quote(s))]


def get_price(symbol: str) -> float | None:
    q = get_quote(symbol)
    return q["price"] if q else None
