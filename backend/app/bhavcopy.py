"""Official exchange Bhavcopy (end-of-day) data layer.

NSE full bhavcopy (nsearchives) and BSE UDiFF bhavcopy (bseindia.com direct
.CSV — the .zip URL serves an HTML block page) are downloaded once per trading
day into data/bhavcopy/raw/{nse,bse}/YYYYMMDD.csv and merged into per-exchange
history panels (data/history/{nse,bse}_panel.csv.gz) keyed by Yahoo ticker.
The panels are the pipeline's primary price source: they are official exchange
data and, unlike Yahoo, they cover BSE scrips. NSE rows also carry delivery
quantity / delivery % — a genuine-buying signal the trader score uses.

Downloads are resumable: a date whose raw file exists is never re-fetched,
and dates that produced no file (holidays) are remembered in missing.txt
(today is never marked missing — its file appears in the evening).
"""
import io, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "bhavcopy" / "raw"
HIST = ROOT / "data" / "history"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
NSE_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{:%d%m%Y}.csv"
BSE_URL = "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{:%Y%m%d}_F_0000.CSV"
PANEL_COLS = ["Key", "Date", "Open", "High", "Low", "Close", "Volume", "DelivPer", "DelivQty"]


def raw_path(exchange, d):
    return RAW / exchange / f"{d:%Y%m%d}.csv"


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8-sig", "ignore")


def download_day(exchange, d, retries=1):
    """Fetch one day's bhavcopy. Returns 'ok' | 'missing' | 'exists'."""
    p = raw_path(exchange, d)
    if p.exists():
        return "exists"
    url = (NSE_URL if exchange == "nse" else BSE_URL).format(d)
    head = "SYMBOL" if exchange == "nse" else "TradDt"
    for attempt in range(retries + 1):
        try:
            text = _fetch(url)
            if text.lstrip().startswith(head) and len(text) > 2000:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
                return "ok"
            return "missing"  # HTML block page / empty = no file for this date
        except Exception:
            if attempt < retries:
                time.sleep(1.5)
    return "missing"


def _missing_file(exchange):
    return RAW / exchange / "missing.txt"


def load_missing(exchange):
    f = _missing_file(exchange)
    if not f.exists():
        return set()
    return {ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()}


def mark_missing(exchange, d):
    if d >= date.today():
        return
    f = _missing_file(exchange)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(f"{d:%Y%m%d}\n")


def existing_dates(exchange):
    d = RAW / exchange
    if not d.exists():
        return []
    out = []
    for p in d.glob("*.csv"):
        try:
            out.append(date(int(p.stem[:4]), int(p.stem[4:6]), int(p.stem[6:8])))
        except Exception:
            continue
    return sorted(out)


def download_range(exchange, start, end, log=print, workers=4):
    """Download every weekday in [start, end] not already present/marked.
    Returns (new_files, attempted)."""
    missing = load_missing(exchange)
    todo, d = [], start
    while d <= end:
        if d.weekday() < 5 and f"{d:%Y%m%d}" not in missing and not raw_path(exchange, d).exists():
            todo.append(d)
        d += timedelta(days=1)
    if not todo:
        log(f"[bhavcopy:{exchange}] up to date ({len(existing_dates(exchange))} files)")
        return 0, 0
    log(f"[bhavcopy:{exchange}] downloading {len(todo)} daily files…")
    got = 0
    def one(day):
        r = download_day(exchange, day)
        if r == "missing":
            mark_missing(exchange, day)
        return r
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(one, todo)):
            if r == "ok":
                got += 1
            if (i + 1) % 50 == 0:
                log(f"[bhavcopy:{exchange}] {i + 1}/{len(todo)} attempted, {got} files ok")
    log(f"[bhavcopy:{exchange}] done: {got} new files of {len(todo)} attempted")
    return got, len(todo)


# ---------------- parsers ----------------

def parse_nse(text):
    """NSE full bhavcopy text -> DataFrame[Date, Symbol, Series, Open, High,
    Low, Close, Volume, DelivQty, DelivPer]."""
    df = pd.read_csv(io.StringIO(text), skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    out = pd.DataFrame({
        "Date": pd.to_datetime(df["DATE1"], format="%d-%b-%Y", errors="coerce"),
        "Symbol": df["SYMBOL"].astype(str).str.strip(),
        "Series": df["SERIES"].astype(str).str.strip(),
        "Open": pd.to_numeric(df["OPEN_PRICE"], errors="coerce"),
        "High": pd.to_numeric(df["HIGH_PRICE"], errors="coerce"),
        "Low": pd.to_numeric(df["LOW_PRICE"], errors="coerce"),
        "Close": pd.to_numeric(df["CLOSE_PRICE"], errors="coerce"),
        "Volume": pd.to_numeric(df["TTL_TRD_QNTY"], errors="coerce"),
        "DelivQty": pd.to_numeric(df["DELIV_QTY"], errors="coerce"),
        "DelivPer": pd.to_numeric(df["DELIV_PER"], errors="coerce"),
    })
    return out.dropna(subset=["Date", "Close"]).query("Close > 0").reset_index(drop=True)


def parse_bse(text):
    """BSE UDiFF bhavcopy text -> DataFrame[Date, Scrip, Ticker, ISIN, Name,
    Open, High, Low, Close, Volume] — cash-segment equity shares only."""
    df = pd.read_csv(io.StringIO(text), dtype=str, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df = df[(df["Sgmt"] == "CM") & (df["FinInstrmTp"] == "STK")]
    def num(col):
        return pd.to_numeric(df[col].astype(str).str.strip(), errors="coerce")
    out = pd.DataFrame({
        "Date": pd.to_datetime(df["TradDt"], errors="coerce"),
        "Scrip": df["FinInstrmId"].astype(str).str.strip(),
        "Ticker": df["TckrSymb"].astype(str).str.strip(),
        "ISIN": df["ISIN"].astype(str).str.strip(),
        "Name": df["FinInstrmNm"].astype(str).str.strip(),
        "Open": num("OpnPric"), "High": num("HghPric"), "Low": num("LwPric"),
        "Close": num("ClsPric"), "Volume": num("TtlTradgVol"),
    })
    out["DelivQty"] = pd.NA
    out["DelivPer"] = pd.NA
    return out.dropna(subset=["Date", "Close"]).query("Close > 0").reset_index(drop=True)


# ---------------- panel build ----------------

def build_panels(universe, log=print):
    """Merge all raw daily files into per-exchange panels keyed by Yahoo
    ticker. Returns coverage dict (also saved to data/history/panel_meta.json)."""
    listings = universe["listings"]
    nse_series = {l["symbol"]: l.get("series", "EQ") for l in listings if l["exchange"] == "NSE"}
    bse_codes = {l["scrip_code"] for l in listings if l["exchange"] == "BSE"}
    bse_isin = {l["isin"]: l["scrip_code"] for l in listings
                if l["exchange"] == "BSE" and l.get("isin")}

    frames = {"nse": [], "bse": []}
    for ex in ("nse", "bse"):
        for d in existing_dates(ex):
            try:
                text = raw_path(ex, d).read_text(encoding="utf-8")
                parsed = parse_nse(text) if ex == "nse" else parse_bse(text)
            except Exception as e:
                log(f"[bhavcopy] skip {ex} {d}: {e}")
                continue
            if ex == "nse":
                parsed = parsed[parsed["Symbol"].isin(nse_series)]
                # one row per symbol per day: prefer the listing's own series
                parsed["_pref"] = [0 if s == nse_series.get(sym) else 1
                                    for sym, s in zip(parsed["Symbol"], parsed["Series"])]
                parsed = (parsed.sort_values("_pref")
                          .drop_duplicates(subset=["Date", "Symbol"], keep="first"))
                parsed["Key"] = parsed["Symbol"] + ".NS"
            else:
                keep = parsed["Scrip"].isin(bse_codes)
                # ISIN fallback for scrips whose code changed / wasn't in master
                fb = (~keep) & parsed["ISIN"].isin(bse_isin)
                parsed.loc[fb, "Scrip"] = parsed.loc[fb, "ISIN"].map(bse_isin)
                parsed = parsed[parsed["Scrip"].isin(bse_codes)]
                parsed["Key"] = parsed["Scrip"] + ".BO"
            frames[ex].append(parsed[["Key", "Date", "Open", "High", "Low", "Close",
                                      "Volume", "DelivPer", "DelivQty"]])
        log(f"[bhavcopy] {ex}: merged {len(frames[ex])} daily files")

    HIST.mkdir(parents=True, exist_ok=True)
    meta = {}
    for ex in ("nse", "bse"):
        if not frames[ex]:
            meta[ex] = dict(rows=0, symbols=0, first=None, last=None)
            continue
        panel = pd.concat(frames[ex], ignore_index=True)
        panel = (panel.drop_duplicates(subset=["Key", "Date"], keep="last")
                 .sort_values(["Key", "Date"]).reset_index(drop=True))
        panel.to_csv(HIST / f"{ex}_panel.csv.gz", index=False, compression="gzip")
        meta[ex] = dict(rows=int(len(panel)), symbols=int(panel["Key"].nunique()),
                        first=str(panel["Date"].min().date()), last=str(panel["Date"].max().date()),
                        files=len(frames[ex]))
        log(f"[bhavcopy] {ex} panel: {meta[ex]['rows']:,} rows, "
            f"{meta[ex]['symbols']:,} symbols, {meta[ex]['first']}..{meta[ex]['last']}")
    (HIST / "panel_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def top_up(months_back=14, log=print):
    """Fetch any missing recent daily files for both exchanges and rebuild
    the panels if anything new arrived. Never raises."""
    try:
        from app import universe as univ_mod
        uni = univ_mod.load_universe()
    except Exception as e:
        log(f"[bhavcopy] top-up skipped (universe): {e}")
        return None
    start = date.today() - timedelta(days=int(months_back * 30.5))
    new_total = 0
    for ex in ("nse", "bse"):
        try:
            got, _ = download_range(ex, start, date.today(), log=log)
            new_total += got
        except Exception as e:
            log(f"[bhavcopy] top-up {ex} failed: {e}")
    meta_f = HIST / "panel_meta.json"
    if new_total or not meta_f.exists():
        try:
            return build_panels(uni, log=log)
        except Exception as e:
            log(f"[bhavcopy] panel rebuild failed: {e}")
    return None
