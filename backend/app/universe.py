"""Build the full Indian equity universe: NSE (official EQUITY_L.csv) + BSE
(BSE scrip master via Upstox's published BSE instrument file — bseindia.com's
own API bot-blocks programmatic access with HTTP 403 from this environment;
the instrument master carries the official BSE scrip codes, which are what
Yahoo Finance uses for .BO tickers)."""
import csv, gzip, io, json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_FILE = ROOT / "data" / "universe_india.json"
NSE_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
UPSTOX_BSE_URL = "https://assets.upstox.com/market-quote/instruments/exchange/BSE.csv.gz"
DEBT = re.compile(r"%|NCD|DEBENTURE|\bBOND|PVT|-CP\b|SDL|GSEC", re.I)

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read()

def parse_nse(text):
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        sym = (row.get("SYMBOL") or "").strip(); series = (row.get(" SERIES") or "").strip()
        if not sym: continue
        out.append(dict(symbol=sym, name=(row.get("NAME OF COMPANY") or "").strip(),
                        exchange="NSE", series=series, isin=(row.get(" ISIN NUMBER") or "").strip(),
                        yahoo=f"{sym}.NS"))
    return out

def parse_bse(raw_gz):
    out = []
    with gzip.GzipFile(fileobj=io.BytesIO(raw_gz)) as gz:
        for row in csv.DictReader(io.TextIOWrapper(gz, encoding="utf-8")):
            if row.get("instrument_type") != "EQUITY" or row.get("exchange") != "BSE_EQ": continue
            tok = (row.get("exchange_token") or "").strip(); sym = (row.get("tradingsymbol") or "").strip()
            name = (row.get("name") or "").strip()
            if not tok.isdigit() or tok[0] not in "56": continue
            if not sym or not sym[0].isalpha(): continue
            if DEBT.search(name) or DEBT.search(sym) or re.search(r"-\d", name): continue
            isin = row["instrument_key"].split("|")[-1] if "|" in row.get("instrument_key","") else ""
            out.append(dict(symbol=sym, scrip_code=tok, name=name, exchange="BSE", series="EQ",
                            isin=isin if isin.startswith("IN") else "", yahoo=f"{tok}.BO"))
    # dedupe by scrip code
    seen = {}
    for r in out: seen[r["scrip_code"]] = r
    return list(seen.values())

def build_universe(save=True):
    nse = parse_nse(_get(NSE_URL).decode("utf-8-sig", "ignore"))
    bse = parse_bse(_get(UPSTOX_BSE_URL))
    data = dict(source_nse=NSE_URL, source_bse="BSE scrip master via Upstox BSE instrument file (bseindia.com API returns 403 to programs)",
                counts=dict(nse=len(nse), bse=len(bse), total=len(nse)+len(bse)), listings=nse+bse)
    if save:
        UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        UNIVERSE_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data

def load_universe():
    if UNIVERSE_FILE.exists(): return json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))
    return build_universe()

if __name__ == "__main__":
    d = build_universe(); print(d["counts"])
