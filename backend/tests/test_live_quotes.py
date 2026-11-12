import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app import datafeed, main


def _ohlc(index, close):
    close = pd.Series(close, index=index, dtype=float)
    return pd.DataFrame({
        "Open": close, "High": close, "Low": close, "Close": close, "Volume": 1000.0,
    })


def test_live_quote_matches_chart_when_panel_is_behind(monkeypatch):
    old = pd.bdate_range("2026-09-01", periods=30)
    new = pd.bdate_range("2026-09-01", periods=40)
    local = _ohlc(old, 100.0)
    yahoo = _ohlc(new, [100.0] * 39 + [130.0])
    monkeypatch.setattr(datafeed, "local_history", lambda t: local.copy())
    monkeypatch.setattr(datafeed, "expected_session_date", lambda: new[-1].date())
    monkeypatch.setattr(
        datafeed, "_yahoo_batch",
        lambda tickers, period="1mo": {t: yahoo.copy() for t in tickers},
    )
    series = datafeed.history_series("RELIANCE.NS", days=5)
    frame = datafeed.with_latest_sessions(["RELIANCE.NS"])["RELIANCE.NS"]
    assert series[-1]["close"] == 130.0
    assert round(float(frame["Close"].iloc[-1]), 2) == 130.0

    main._LIVE_CACHE.clear()
    monkeypatch.setattr(main, "_resolve_yahoo_map", lambda symbols, hints=None: {s: f"{s}.NS" for s in symbols})
    monkeypatch.setattr(main, "_latest", lambda: None)
    quotes = main.get_live_quotes(["RELIANCE"])
    assert quotes["RELIANCE"] == series[-1]["close"]


def test_fresh_panel_is_not_replaced(monkeypatch):
    old = pd.bdate_range("2026-09-01", periods=30)
    local = _ohlc(old, 100.0)
    called = []
    monkeypatch.setattr(datafeed, "local_history", lambda t: local.copy())
    monkeypatch.setattr(datafeed, "expected_session_date", lambda: old[-1].date())

    def _no_yahoo(tickers, period="1mo"):
        called.append(list(tickers))
        return {}

    monkeypatch.setattr(datafeed, "_yahoo_batch", _no_yahoo)
    series = datafeed.history_series("RELIANCE.NS", days=3)
    frame = datafeed.with_latest_sessions(["RELIANCE.NS"])["RELIANCE.NS"]
    assert called == []
    assert series[-1]["close"] == 100.0
    assert float(frame["Close"].iloc[-1]) == 100.0
