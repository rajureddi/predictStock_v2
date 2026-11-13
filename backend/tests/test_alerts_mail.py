import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app import alerts, mailer

IST = ZoneInfo("Asia/Kolkata")


def test_stop_rings_once():
    rules = [{"id": "pick-TCS-stop", "symbol": "TCS", "type": "stop", "price": 3500, "enabled": True, "note": "TCS stop"}]
    rings, state = alerts.evaluate(rules, {"TCS": 3490})
    assert len(rings) == 1 and rings[0]["id"] == "pick-TCS-stop"
    again, _ = alerts.evaluate(rules, {"TCS": 3400}, state)
    assert again == []


def test_target_waits_for_the_price():
    rules = [{"id": "t", "symbol": "INFY", "type": "target", "price": 1600, "enabled": True}]
    rings, _ = alerts.evaluate(rules, {"INFY": 1500})
    assert rings == []
    rings, _ = alerts.evaluate(rules, {"INFY": 1600})
    assert rings[0]["type"] == "target"


def test_massive_selling_uses_the_scan_price():
    rules = [{"id": "d", "symbol": "SBIN", "type": "massive_selling", "entry_price": 1000, "pct": 2.5, "direction": "down", "enabled": True}]
    quiet, _ = alerts.evaluate(rules, {"SBIN": 980})
    hit, _ = alerts.evaluate(rules, {"SBIN": 970})
    assert quiet == [] and hit[0]["symbol"] == "SBIN"


def test_cutoff_rings_after_1520_ist():
    rules = [{"id": "system-cutoff-1520", "symbol": "MARKET", "type": "cutoff", "at": "15:20", "enabled": True}]
    morning = datetime(2026, 11, 12, 10, 0, tzinfo=IST)
    evening = datetime(2026, 11, 12, 15, 25, tzinfo=IST)
    assert alerts.evaluate(rules, {}, now=morning)[0] == []
    rings, state = alerts.evaluate(rules, {}, now=evening)
    assert rings[0]["type"] == "cutoff"
    assert alerts.evaluate(rules, {}, state, now=evening)[0] == []
    next_day = datetime(2026, 11, 13, 15, 25, tzinfo=IST)
    again, _ = alerts.evaluate(rules, {}, state, now=next_day)
    assert again[0]["type"] == "cutoff"


def test_morning_starts_each_weekday_at_7_and_mails_when_the_scan_finishes():
    from app import morning
    monday_early = datetime(2026, 11, 16, 6, 50, tzinfo=IST)
    monday_open_window = datetime(2026, 11, 16, 7, 0, tzinfo=IST)
    monday_done = datetime(2026, 11, 16, 8, 10, tzinfo=IST)
    friday = datetime(2026, 11, 13, 7, 30, tzinfo=IST)
    saturday = datetime(2026, 11, 14, 7, 30, tzinfo=IST)
    assert morning.decide(friday, {}, False, None)["start"] is True
    assert morning.decide(saturday, {}, False, None)["start"] is False
    assert morning.decide(monday_early, {}, False, None)["start"] is False
    started = morning.decide(monday_open_window, {}, False, None)
    assert started["start"] is True and started["send"] is False
    already = morning.decide(monday_open_window, {}, False, "2026-11-16")
    assert already["start"] is False and already["send"] is True
    waiting = morning.decide(monday_done, started["state"], True, None)
    assert waiting["start"] is False and waiting["send"] is False
    finished = morning.decide(monday_done, started["state"], False, "2026-11-16")
    assert finished["send"] is True


def test_report_text_lists_the_pick():
    text = mailer.report_text({"run_date": "2026-11-11", "target_date": "2026-11-18", "picks": [
        {"symbol": "CORONA", "exchange": "NSE", "name": "CORONA Remedies", "current_price": 100, "predicted_price": 110, "stop_loss": 90, "target": 120, "reasons": ["Above 21-EMA"]}
    ]}, holdings=[])
    assert "CORONA" in text and "₹100.00" in text and "Above 21-EMA" in text


def test_report_html_includes_predictions_and_portfolio():
    html = mailer.report_html(
        {"run_date": "2026-11-11", "target_date": "2026-11-18", "picks": [
            {"symbol": "CORONA", "exchange": "NSE", "name": "CORONA Remedies", "current_price": 100,
             "predicted_price": 110, "predicted_return_pct": 7.83, "stop_loss": 90, "target": 120, "reasons": ["Above 21-EMA"]}
        ]},
        holdings=[{"symbol": "LAURUSLABS", "name": "Laurus Labs", "shares": 4, "buy": 500}],
        quotes={"LAURUSLABS": 520},
    )
    assert "<html" in html and "CORONA" in html and "&#8377;100.00" in html and "+7.83%" in html
    assert "Portfolio" in html and "LAURUSLABS" in html and "&#8377;80.00" in html


def test_saved_times_move_the_scan_window_and_several_inboxes():
    from datetime import time as dtime
    from app import morning
    tuesday_early = datetime(2026, 11, 17, 6, 0, tzinfo=IST)
    tuesday_start = datetime(2026, 11, 17, 6, 30, tzinfo=IST)
    assert morning.decide(tuesday_early, {}, False, None, dtime(6, 30), dtime(8, 0))["start"] is False
    assert morning.decide(tuesday_start, {}, False, None, dtime(6, 30), dtime(8, 0))["start"] is True
    found, bad = mailer.parse_recipients("a@x.com, b@x.com\nc@x.com not-an-email")
    assert found == ["a@x.com", "b@x.com", "c@x.com"] and bad == ["not-an-email"]


def test_alert_mail_names_the_stop_and_the_target():
    rings = [
        {"symbol": "TCS", "type": "stop", "price": 3490, "message": "TCS stop-loss at ₹3,500.00 · last close ₹3,490.00"},
        {"symbol": "INFY", "type": "target", "price": 1600, "message": "INFY target 1 at ₹1,600.00 · last close ₹1,600.00"},
    ]
    html = mailer.alert_html(rings)
    text = mailer.alert_text(rings)
    assert "Stop hit" in html and "Target hit" in html and "TCS" in html and "INFY" in text
    assert mailer.alert_subject(rings) == "MarketMind Pro — 2 alerts"
    assert mailer.alert_subject(rings[:1]) == "MarketMind Pro — TCS stop hit"
