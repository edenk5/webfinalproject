import json
import urllib.request
import urllib.parse
import urllib.error
import math
from datetime import datetime, timedelta
import random

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "TSLA", "META", "BRK-B", "JPM", "V",
    "JNJ", "WMT", "XOM", "UNH", "MA",
]

SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Consumer", "NVDA": "Technology", "TSLA": "Automotive",
    "META": "Technology", "BRK-B": "Finance", "JPM": "Finance",
    "V": "Finance", "JNJ": "Healthcare", "WMT": "Consumer",
    "XOM": "Energy", "UNH": "Healthcare", "MA": "Finance",
}

class StockModel:
    @staticmethod
    def _fetch_yahoo_quote(ticker: str) -> dict | None:
        url = (
            f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}"
            "?interval=1d&range=1y"
        )
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
            return data
        except urllib.error.HTTPError as e:
            print(f"Yahoo API Error for {ticker}: HTTP {e.code} - {e.reason}")
            return None
        except Exception as e:
            print(f"Network Error for {ticker}: {e}")
            return None

    @classmethod
    def get_stock_data(cls, ticker: str) -> dict:
        raw = cls._fetch_yahoo_quote(ticker)

        if raw:
            try:
                meta = raw["chart"]["result"][0]["meta"]
                closes = raw["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                timestamps = raw["chart"]["result"][0]["timestamp"]

                closes = [c for c in closes if c is not None]
                current_price = meta.get("regularMarketPrice", closes[-1] if closes else 0)
                prev_close    = meta.get("previousClose", closes[-2] if len(closes) > 1 else current_price)
                week52_high   = meta.get("fiftyTwoWeekHigh", max(closes))
                week52_low    = meta.get("fiftyTwoWeekLow",  min(closes))
                volume        = meta.get("regularMarketVolume", 0)
                currency      = meta.get("currency", "USD")
                exchange      = meta.get("exchangeName", "")

                change        = current_price - prev_close
                change_pct    = (change / prev_close * 100) if prev_close else 0

                year_change_pct = ((current_price - closes[0]) / closes[0] * 100) if closes else 0

                raw_prices = closes[-90:]
                raw_ts     = timestamps[-90:]

                history_prices = []
                history_dates  = []
                for i, ts in enumerate(raw_ts):
                    try:
                        history_dates.append(
                            datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                        )
                        history_prices.append(round(raw_prices[i], 2))
                    except Exception:
                        pass

                today_str = datetime.utcnow().strftime("%Y-%m-%d")
                if not history_dates or history_dates[-1] != today_str:
                    history_dates.append(today_str)
                    history_prices.append(round(current_price, 2))
                else:
                    history_prices[-1] = round(current_price, 2)

                score, signal, signal_class, reasoning = cls._score_stock(
                    current_price, prev_close, week52_high, week52_low,
                    closes, year_change_pct, volume
                )

                return {
                    "ticker": ticker,
                    "name": meta.get("longName") or meta.get("shortName") or ticker,
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "week52_high": round(week52_high, 2),
                    "week52_low": round(week52_low, 2),
                    "volume": volume,
                    "currency": currency,
                    "exchange": exchange,
                    "year_change_pct": round(year_change_pct, 2),
                    "history_prices": history_prices,
                    "history_dates": history_dates,
                    "sector": SECTOR_MAP.get(ticker, "Other"),
                    "score": score,
                    "signal": signal,
                    "signal_class": signal_class,
                    "reasoning": reasoning,
                    "live": True,
                }
            except (KeyError, IndexError, TypeError):
                pass

        return cls._synthetic_stock(ticker)

    @staticmethod
    def _score_stock(price, prev_close, high52, low52, closes, year_pct, volume) -> tuple:
        reasoning = []
        score = 50 
        sma30 = sum(closes[-30:]) / len(closes[-30:]) if len(closes) >= 30 else price
        if price > sma30 * 1.02:
            score += 15
            reasoning.append("📈 Price is 2%+ above 30-day average — bullish momentum")
        elif price > sma30:
            score += 7
            reasoning.append("📊 Price slightly above 30-day average")
        elif price < sma30 * 0.98:
            score -= 12
            reasoning.append("📉 Price is below 30-day average — bearish pressure")

        rng = high52 - low52
        if rng > 0:
            pos = (price - low52) / rng
            if pos > 0.85:
                score += 8
                reasoning.append("🏆 Near 52-week high — strong trend")
            elif pos < 0.25:
                score -= 10
                reasoning.append("⚠️ Near 52-week low — potential weakness or value")

        if year_pct > 30:
            score += 12
            reasoning.append(f"🚀 Up {year_pct:.1f}% over past year — strong long-term trend")
        elif year_pct < -20:
            score -= 12
            reasoning.append(f"🔻 Down {abs(year_pct):.1f}% over past year")

        score = max(0, min(100, score))

        if score >= 72: signal = "STRONG BUY"
        elif score >= 57: signal = "BUY"
        elif score >= 43: signal = "HOLD"
        elif score >= 28: signal = "SELL"
        else: signal = "STRONG SELL"

        return score, signal, signal.replace(" ", "-"), reasoning

    @staticmethod
    def _synthetic_stock(ticker: str) -> dict:
        seed = sum(ord(c) for c in ticker)
        rng  = random.Random(seed)
        base_price   = rng.uniform(50, 800)
        return {
            "ticker": ticker, "name": f"{ticker} Inc.", "price": round(base_price, 2),
            "change": 0, "change_pct": 0, "week52_high": base_price * 1.2,
            "week52_low": base_price * 0.8, "volume": 10000, "currency": "USD",
            "exchange": "NASDAQ", "year_change_pct": 0,
            "history_prices": [base_price] * 90, "history_dates": [],
            "sector": "Other", "score": 50, "signal": "HOLD",
            "signal_class": "HOLD", "reasoning": ["Using simulated data"], "live": False
        }

    @classmethod
    def get_all_stocks(cls, tickers: list[str] | None = None) -> list[dict]:
        return [cls.get_stock_data(t) for t in (tickers or DEFAULT_TICKERS)]

    @classmethod
    def get_top_picks(cls, stocks: list[dict], n: int = 5) -> list[dict]:
        return sorted(stocks, key=lambda s: s["score"], reverse=True)[:n]

    @staticmethod
    def get_sector_summary(stocks: list[dict]) -> dict:
        sectors = {}
        for s in stocks:
            sectors.setdefault(s["sector"], []).append(s["score"])
        return {sec: round(sum(scores) / len(scores), 1) for sec, scores in sectors.items()}
