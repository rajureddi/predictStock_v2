import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import report_store


def _use_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(report_store, "REPORTS", tmp_path)
    monkeypatch.setattr(report_store, "DB_PATH", tmp_path / "reports.db")


def test_same_week_scans_are_all_kept(tmp_path, monkeypatch):
    _use_tmp(tmp_path, monkeypatch)
    report_store.save_report({"run_date": "2026-11-02", "target_date": "2026-11-09", "picks": [{"symbol": "AAA"}]})
    report_store.save_report({"run_date": "2026-11-03", "target_date": "2026-11-10", "picks": [{"symbol": "BBB"}]})
    dates = [r["run_date"] for r in report_store.list_reports()]
    assert dates == ["2026-11-03", "2026-11-02"]
    assert report_store.get_report("2026-11-02")["picks"][0]["symbol"] == "AAA"


def test_json_import_moves_day_into_db(tmp_path, monkeypatch):
    _use_tmp(tmp_path, monkeypatch)
    src = tmp_path / "report-2026-11-01.json"
    src.write_text(json.dumps({
        "run_date": "2026-11-01",
        "target_date": "2026-11-08",
        "picks": [{"symbol": "NOV1"}],
    }), encoding="utf-8")
    (tmp_path / "latest.json").write_text("{}", encoding="utf-8")
    assert report_store.import_json_reports() == 1
    assert not src.exists()
    assert (tmp_path / "latest.json").exists()
    got = report_store.get_report("2026-11-01")
    assert got["target_date"] == "2026-11-08"
    assert got["picks"][0]["symbol"] == "NOV1"


def test_rescan_same_day_replaces_row(tmp_path, monkeypatch):
    _use_tmp(tmp_path, monkeypatch)
    report_store.save_report({"run_date": "2026-11-02", "picks": [{"symbol": "OLD"}]})
    report_store.save_report({"run_date": "2026-11-02", "picks": [{"symbol": "NEW"}]})
    dates = report_store.list_dates()
    assert len(dates) == 1
    assert dates[0]["pick_count"] == 1
    assert report_store.latest_report()["picks"][0]["symbol"] == "NEW"
