"""V2: bhavcopy parsers, delivery scoring, fundamentals, news, demotion."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app import bhavcopy
from app.engine import trader_score
from app.fundamentals import score_fundamentals, severe_red_flag
from app.news import analyse_headlines
from app.pipeline import apply_red_flag_demotion, rank_key, dedupe_by_isin

NSE_SAMPLE = """SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER
RELIANCE, EQ, 22-Oct-2026, 1400.00, 1405.00, 1425.00, 1398.00, 1418.00, 1416.50, 1410.20, 5234100, 73800.50, 312000, 2980000, 56.94
TCS, EQ, 22-Oct-2026, 3050.00, 3048.00, 3080.00, 3030.00, 3062.00, 3058.00, 3055.00, 1200300, 36680.10, 98000, 610000, 50.82
"""

BSE_HEADER = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,"
              "FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,"
              "LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,"
              "TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4")
BSE_SAMPLE = BSE_HEADER + """
2026-10-22,2026-10-22,CM,BSE,STK,500002,INE117A01022,ABB,A,,,,,ABB INDIA LIMITED,6550.00,6590.00,6392.95,6460.00,6460.00,6562.00,,6464.47,,,21706,140346129.00,3084,F1,1,,,,,
2026-10-22,2026-10-22,CM,BSE,DBT,800001,INE000X01000,FAKEDEB,X,,,,,SOME DEBENTURE,100.00,101.00,99.00,100.50,100.50,100.00,,,5000,502500.00,10,F1,1,,,,,
"""


def test_parse_nse_bhavcopy():
    df = bhavcopy.parse_nse(NSE_SAMPLE)
    assert len(df) == 2
    r = df[df["Symbol"] == "RELIANCE"].iloc[0]
    assert r["Close"] == 1416.50 and r["Volume"] == 5234100
    assert abs(r["DelivPer"] - 56.94) < 0.01 and r["DelivQty"] == 2980000
    assert str(df["Date"].iloc[0].date()) == "2026-10-22"


def test_parse_bse_udiff_filters_to_equity():
    df = bhavcopy.parse_bse(BSE_SAMPLE)
    assert len(df) == 1  # debenture row filtered out
    r = df.iloc[0]
    assert r["Scrip"] == "500002" and r["Ticker"] == "ABB" and r["ISIN"] == "INE117A01022"
    assert r["Close"] == 6460.00 and r["Volume"] == 21706
    assert str(r["Date"].date()) == "2026-10-22"


def _frame(n=120, last_jump=0.05, deliv=None):
    close = np.linspace(100, 150, n)
    close[-1] = close[-2] * (1 + last_jump)
    open_ = np.roll(close, 1); open_[0] = close[0]
    idx = pd.bdate_range("2026-01-01", periods=n)
    df = pd.DataFrame({"Open": open_, "High": np.maximum(open_, close) * 1.004,
                       "Low": np.minimum(open_, close) * 0.996, "Close": close,
                       "Volume": np.full(n, 500_000.0)}, index=idx)
    if deliv is not None:
        df["DelivPer"] = float(deliv)
        df["DelivQty"] = 1000.0
    return df


def test_delivery_high_adds_score_and_reason():
    base = trader_score(_frame())
    withd = trader_score(_frame(deliv=62.0))
    assert withd["metrics"]["delivery_pct"] == 62.0
    assert any("High delivery" in r for r in withd["reasons"])
    assert withd["score"] == min(100.0, base["score"] + 3)


def test_delivery_low_on_big_up_day_penalised():
    base = trader_score(_frame())
    lowd = trader_score(_frame(deliv=10.0))
    assert any("Low delivery" in r for r in lowd["reasons"])
    assert lowd["score"] == max(0.0, base["score"] - 2)


def test_delivery_absent_is_noop():
    ts = trader_score(_frame())
    assert ts["metrics"]["delivery_pct"] is None
    assert not any("delivery" in r.lower() for r in ts["reasons"])


def test_fundamentals_scoring_and_flags():
    s, flags = score_fundamentals(dict(pe=18.0, roe=0.24, debt_to_equity=0.3,
                                       revenue_growth=0.22, earnings_growth=0.35))
    assert s > 80 and any("Strong ROE" in f for f in flags)
    s2, flags2 = score_fundamentals(dict(pe=-4.0, roe=0.02, debt_to_equity=3.6,
                                         revenue_growth=-0.1, earnings_growth=-0.22))
    assert s2 < 30 and any("Loss-making" in f for f in flags2) and any("High debt" in f for f in flags2)
    s3, flags3 = score_fundamentals(dict(pe=None, roe=None, debt_to_equity=None,
                                         revenue_growth=None, earnings_growth=None))
    assert s3 == 50.0 and flags3 == []


def test_severe_red_flag_rule():
    assert severe_red_flag(dict(debt_to_equity=3.6, earnings_growth=-0.1)) is True
    assert severe_red_flag(dict(debt_to_equity=3.6, earnings_growth=0.1)) is False
    assert severe_red_flag(dict(debt_to_equity=1.0, earnings_growth=-0.1)) is False
    assert severe_red_flag(None) is False


def test_news_veto_and_sentiment():
    bad = analyse_headlines([{"title": "SEBI raids offices of XYZ Ltd in fraud probe"}])
    assert bad["veto"] is True and "fraud" in bad["veto_reason"].lower()
    good = analyse_headlines([{"title": "ABC bags order worth Rs 500 crore"},
                              {"title": "ABC Q2 PAT doubles on strong demand"}])
    assert good["veto"] is False and good["sentiment_label"] == "Positive"
    neg = analyse_headlines([{"title": "PQR shares plunge as loss widens in Q2"}])
    assert neg["sentiment_label"] == "Negative"
    none = analyse_headlines([])
    assert none["veto"] is False and none["sentiment_label"] == "Neutral"


def _pick(sym, fund=None):
    return dict(symbol=sym, fundamentals=fund, trader_score=80.0,
                predicted_return_pct=5.0, backtest={"best_dir_acc": 70.0})


def test_red_flag_demotion():
    flagged = _pick("BAD", dict(debt_to_equity=4.0, earnings_growth=-0.3, score=20, flags=["High debt"]))
    ranked = [flagged] + [_pick(f"C{i}") for i in range(8)]
    pool, demoted = apply_red_flag_demotion(ranked, keep=7)
    assert [p["symbol"] for p in demoted] == ["BAD"] and len(pool) == 8
    # not enough clean picks -> nobody demoted
    ranked2 = [flagged] + [_pick(f"C{i}") for i in range(5)]
    pool2, demoted2 = apply_red_flag_demotion(ranked2, keep=7)
    assert demoted2 == [] and len(pool2) == 6


def test_dedupe_by_isin_keeps_best_listing():
    nse = dict(symbol="PCJEWELLER", exchange="NSE", isin="INE785M01021", yahoo="PCJEWELLER.NS")
    bse = dict(symbol="PCJEWELLER", exchange="BSE", isin="INE785M01021", yahoo="534809.BO")
    other = dict(symbol="SSWL", exchange="BSE", isin="INE999X01000", yahoo="513262.BO")
    noisin = dict(symbol="XYZ", exchange="BSE", isin=None, yahoo="500001.BO")
    kept, dropped = dedupe_by_isin([nse, bse, other, noisin])
    assert [p["yahoo"] for p in kept] == ["PCJEWELLER.NS", "513262.BO", "500001.BO"]
    assert [p["yahoo"] for p in dropped] == ["534809.BO"]


def test_rank_key_rewards_fundamentals():
    strong = _pick("S", dict(score=90))
    weak = _pick("W", dict(score=10))
    none_f = _pick("N", None)
    assert rank_key(strong) < rank_key(none_f) < rank_key(weak)
