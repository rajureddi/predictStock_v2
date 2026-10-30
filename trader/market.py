#!/usr/bin/env python3
"""MarketMind Pro Indian Market Utility for Day Trader Skills.

Provides market timings, IST timezone conversions (+5:30), Yahoo Finance symbol
routing (.NS/.BO), and holiday calendars for NSE (National Stock Exchange of India)
and BSE, while maintaining dual-mode compatibility for US stocks and test fixtures.
"""

import datetime
import os
import re

# Fixed offset for Indian Standard Time (IST): UTC + 5:30 (no DST)
IST_DELTA = datetime.timedelta(hours=5, minutes=30)
EPOCH = datetime.datetime(1970, 1, 1)

# Trading session constants
NSE_OPEN = datetime.time(9, 15)
NSE_CLOSE = datetime.time(15, 30)
NSE_OPEN_MIN = 9 * 60 + 15     # 555
NSE_CLOSE_MIN = 15 * 60 + 30   # 930
NSE_SESSION_BARS = 75          # 375 minutes / 5 = 75 bars

NYSE_OPEN = datetime.time(9, 30)
NYSE_CLOSE = datetime.time(16, 0)
NYSE_OPEN_MIN = 9 * 60 + 30    # 570
NYSE_CLOSE_MIN = 16 * 60       # 960
NYSE_SESSION_BARS = 78         # 390 minutes / 5 = 78 bars

# NSE Trading Holidays (Gazetted & Exchange holidays)
NSE_HOLIDAYS = {
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-03-20": "Id-Ul-Fitr (Ramzan Id)",
    "2026-03-27": "Ram Navami",
    "2026-03-31": "Mahavir Jayanti",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-27": "Bakri Id",
    "2026-06-26": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-08": "Diwali Laxmi Pujan",
    "2026-11-10": "Diwali Balipratipada",
    "2026-11-24": "Guru Nanak Jayanti",
    "2026-12-25": "Christmas",
    "2027-01-26": "Republic Day",
    "2027-03-22": "Holi",
    "2027-03-26": "Good Friday",
    "2027-04-14": "Ambedkar Jayanti",
    "2027-05-01": "Maharashtra Day",
    "2027-08-15": "Independence Day",
    "2027-10-02": "Mahatma Gandhi Jayanti",
    "2027-12-25": "Christmas",
}

NYSE_HOLIDAYS = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King, Jr. Day",
    "2026-02-16": "Washington's Birthday",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King, Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed)",
}

NYSE_EARLY_CLOSE = {
    "2026-11-27": "day after Thanksgiving",
    "2026-12-24": "Christmas Eve",
    "2027-11-26": "day after Thanksgiving",
}

US_TICKERS = {
    "TSLA", "AAPL", "NVDA", "MSFT", "AMZN", "GOOG", "GOOGL", "META",
    "SPY", "QQQ", "KO", "BAC", "AXP", "BRK-B", "BRK.B"
}

def is_indian_stock(sym):
    """Returns True if the symbol is for an Indian market (NSE or BSE)."""
    s = str(sym or "").strip().upper()
    if not s:
        return True
    if s.endswith(".NS") or s.endswith(".BO"):
        return True
    if s.isdigit() and len(s) == 6:
        return True
    if s in US_TICKERS or s.endswith(".US"):
        return False
    # If explicit US symbol format with dot/dash (like BRK-B) and in US list
    if "-" in s and any(s.startswith(u) for u in US_TICKERS):
        return False
    # Default in MarketMind Pro is Indian stock (NSE)
    return True


def to_yahoo_symbol(sym):
    """Converts a user-supplied symbol into the exact ticker Yahoo Finance expects."""
    s = str(sym or "").strip().upper()
    if not s:
        return s
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    if s.isdigit() and len(s) == 6:
        return f"{s}.BO"
    if s in US_TICKERS or s.endswith(".US"):
        return s.replace(".US", "").replace(".", "-")
    if "." in s and not s.endswith((".NS", ".BO")):
        return s.replace(".", "-")
    # Indian stock without suffix: default to NSE (.NS)
    return f"{s}.NS"


def to_ist(utc):
    """Converts naive or aware UTC datetime to naive IST datetime (+5:30)."""
    naive = utc.replace(tzinfo=None)
    return naive + IST_DELTA


def ist_to_utc(local):
    """Converts naive IST datetime to naive UTC datetime."""
    naive = local.replace(tzinfo=None)
    return naive - IST_DELTA


def _nth_sunday(year, month, n):
    d = datetime.date(year, month, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)
    return d + datetime.timedelta(weeks=n - 1)


def eastern_offset(utc):
    """Hours from UTC for New York: -4 in daylight time, -5 otherwise."""
    y = utc.year
    start = datetime.datetime.combine(_nth_sunday(y, 3, 2), datetime.time(7, 0))
    end = datetime.datetime.combine(_nth_sunday(y, 11, 1), datetime.time(6, 0))
    naive = utc.replace(tzinfo=None)
    return -4 if start <= naive < end else -5


def to_eastern(utc):
    return utc.replace(tzinfo=None) + datetime.timedelta(hours=eastern_offset(utc))


def eastern_to_utc(local):
    for off in (-4, -5):
        utc = local - datetime.timedelta(hours=off)
        if eastern_offset(utc) == off:
            return utc
    return local + datetime.timedelta(hours=5)


def to_market_time(utc, sym=None):
    """Converts UTC datetime to the stock's local market time (IST for Indian, ET for US)."""
    if is_indian_stock(sym):
        return to_ist(utc)
    return to_eastern(utc)


def market_to_utc(local, sym=None):
    """Converts local market time to naive UTC datetime."""
    if is_indian_stock(sym):
        return ist_to_utc(local)
    return eastern_to_utc(local)


def get_market_timings(sym=None):
    """Returns (open_time, close_time, open_min, close_min, session_bars, holidays, early_closes)."""
    if is_indian_stock(sym):
        return (
            NSE_OPEN,
            NSE_CLOSE,
            NSE_OPEN_MIN,
            NSE_CLOSE_MIN,
            NSE_SESSION_BARS,
            NSE_HOLIDAYS,
            {} # No early close in NSE
        )
    return (
        NYSE_OPEN,
        NYSE_CLOSE,
        NYSE_OPEN_MIN,
        NYSE_CLOSE_MIN,
        NYSE_SESSION_BARS,
        NYSE_HOLIDAYS,
        NYSE_EARLY_CLOSE
    )


def currency_symbol(sym=None):
    if is_indian_stock(sym):
        return "₹"
    return "$"

