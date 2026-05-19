"""
CONTROLLER LAYER — StockController (Flask Blueprint)
Responsible for: routing, request parsing, calling the Model,
and passing data to Views (templates).
Has zero knowledge of HTML — only orchestrates.
"""

import requests
from flask import Blueprint, render_template, request, jsonify, abort
from models.stock_model import StockModel, DEFAULT_TICKERS

# Create a blueprint — all routes live here, not in app.py
stock_bp = Blueprint("stocks", __name__)

def generate_ai_summary(stock: dict) -> str:
    """
    Calls a local Ollama server to generate a 2-sentence investment summary via RAG.
    Fails gracefully if Ollama is not running.
    """
    prompt = (
        f"You are an expert financial advisor. Based ONLY on the following real-time data, "
        f"write a concise, 2-sentence investment summary for {stock['name']} ({stock['ticker']}).\n"
        f"Current Price: ${stock['price']}\n"
        f"52-Week High: ${stock['week52_high']}\n"
        f"52-Week Low: ${stock['week52_low']}\n"
        f"1-Year Return: {stock['year_change_pct']}%\n"
        f"Algorithm Investment Score: {stock['score']}/100\n"
    )
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=3.0
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except requests.exceptions.RequestException:
        pass
        
    return "AI insights are currently unavailable. Ensure the local Ollama server is running with the 'llama3' model."




# ─────────────────────────────────────────────────────────
# Route: Dashboard  /
# ─────────────────────────────────────────────────────────
@stock_bp.route("/")
def dashboard():
    """Main dashboard — shows market overview + top picks."""
    stocks        = StockModel.get_all_stocks()
    top_picks     = StockModel.get_top_picks(stocks, n=5)
    sector_scores = StockModel.get_sector_summary(stocks)

    # Market-wide stats for hero cards
    total_stocks  = len(stocks)
    avg_score     = round(sum(s["score"] for s in stocks) / total_stocks, 1)
    gainers       = sum(1 for s in stocks if s["change_pct"] > 0)
    losers        = total_stocks - gainers

    return render_template(
        "index.html",
        stocks=stocks,
        top_picks=top_picks,
        sector_scores=sector_scores,
        avg_score=avg_score,
        gainers=gainers,
        losers=losers,
        total_stocks=total_stocks,
    )


# ─────────────────────────────────────────────────────────
# Route: Stock Detail  /stock/<ticker>
# ─────────────────────────────────────────────────────────
@stock_bp.route("/stock/<ticker>")
def stock_detail(ticker: str):
    """Deep-dive view for a single stock."""
    ticker = ticker.upper()
    stock  = StockModel.get_stock_data(ticker)

    if not stock:
        abort(404)

    # Related stocks in same sector (excluding itself)
    all_stocks = StockModel.get_all_stocks()
    related    = [
        s for s in all_stocks
        if s["sector"] == stock["sector"] and s["ticker"] != ticker
    ][:4]

    ai_summary = generate_ai_summary(stock)

    return render_template("stock_detail.html", stock=stock, related=related, ai_summary=ai_summary)


# ─────────────────────────────────────────────────────────
# Route: Watchlist  /watchlist
# ─────────────────────────────────────────────────────────
@stock_bp.route("/watchlist", methods=["GET", "POST"])
def watchlist():
    """User-defined watchlist: GET renders it, POST searches/adds tickers."""
    # Custom tickers come from query string  ?tickers=AAPL,TSLA,...
    tickers_param = request.args.get("tickers", "")
    custom_tickers = (
        [t.strip().upper() for t in tickers_param.split(",") if t.strip()]
        if tickers_param
        else DEFAULT_TICKERS[:8]
    )

    stocks   = StockModel.get_all_stocks(custom_tickers)
    top_pick = StockModel.get_top_picks(stocks, n=1)[0] if stocks else None

    return render_template(
        "watchlist.html",
        stocks=stocks,
        top_pick=top_pick,
        tickers_input=",".join(custom_tickers),
    )


# ─────────────────────────────────────────────────────────
# API Route: /api/stock/<ticker>  (JSON)
# ─────────────────────────────────────────────────────────
@stock_bp.route("/api/stock/<ticker>")
def api_stock(ticker: str):
    """Returns JSON for a single stock — used by client-side JS charts."""
    data = StockModel.get_stock_data(ticker.upper())
    if not data:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


# ─────────────────────────────────────────────────────────
# API Route: /api/stocks  (JSON bulk)
# ─────────────────────────────────────────────────────────
@stock_bp.route("/api/stocks")
def api_stocks():
    """Returns JSON array of all default stocks."""
    return jsonify(StockModel.get_all_stocks())
