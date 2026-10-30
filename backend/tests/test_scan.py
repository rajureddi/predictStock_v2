import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app import scan


def _fake_checkpoint(tmp_path, done=10, total_results=1000, liquid=600):
    results = [dict(symbol=f"S{i}", liquid=(i < liquid)) for i in range(total_results)]
    p = tmp_path / "stage1_checkpoint.json"
    p.write_text(json.dumps({"run_date": "2026-10-24", "results": results,
                             "done_batches": list(range(done))}))
    return p


def test_checkpoint_parsing(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, "CKPT", _fake_checkpoint(tmp_path, done=10))
    monkeypatch.setattr(scan, "_TOTAL_BATCHES", 80)
    prog = scan.checkpoint_progress()
    assert prog == {"done_batches": 10, "total_batches": 80, "results": 1000,
                    "liquid": 600, "run_date": "2026-10-24"}


def test_checkpoint_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, "CKPT", tmp_path / "nope.json")
    assert scan.checkpoint_progress() is None


def test_status_stage1_while_running(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, "CKPT", _fake_checkpoint(tmp_path, done=25))
    monkeypatch.setattr(scan, "_TOTAL_BATCHES", 80)
    monkeypatch.setattr(scan, "scan_running", lambda: (True, [4321]))
    monkeypatch.setattr(scan, "STATE", tmp_path / "scan_state.json")
    s = scan.get_status()
    assert s["running"] is True and s["stage"] == "stage1"
    assert s["stage1"]["done_batches"] == 25 and s["stage1"]["liquid"] == 600


def test_status_stage2_when_checkpoint_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, "CKPT", _fake_checkpoint(tmp_path, done=80))
    monkeypatch.setattr(scan, "_TOTAL_BATCHES", 80)
    monkeypatch.setattr(scan, "scan_running", lambda: (True, [4321]))
    monkeypatch.setattr(scan, "STATE", tmp_path / "scan_state.json")
    s = scan.get_status()
    assert s["running"] is True and s["stage"] == "stage2"


def test_status_done_with_report(tmp_path, monkeypatch):
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"run_date": "2026-10-24", "target_date": "2026-10-31",
                                  "data_as_of": "2026-10-23", "picks": [{}, {}],
                                  "stage_counts": {"universe": 7987}}))
    monkeypatch.setattr(scan, "LATEST", latest)
    monkeypatch.setattr(scan, "CKPT", tmp_path / "nope.json")
    monkeypatch.setattr(scan, "STATE", tmp_path / "scan_state.json")
    monkeypatch.setattr(scan, "scan_running", lambda: (False, []))
    s = scan.get_status()
    assert s["running"] is False and s["stage"] == "done"
    assert s["summary"]["picks_count"] == 2 and s["summary"]["target_date"] == "2026-10-31"


def test_status_failed_after_start_without_report(tmp_path, monkeypatch):
    state = tmp_path / "scan_state.json"
    state.write_text(json.dumps({"started_at": "2999-01-01T00:00:00+00:00", "source": "web"}))
    monkeypatch.setattr(scan, "STATE", state)
    monkeypatch.setattr(scan, "LATEST", tmp_path / "latest.json")  # absent
    monkeypatch.setattr(scan, "CKPT", tmp_path / "nope.json")
    monkeypatch.setattr(scan, "scan_running", lambda: (False, []))
    s = scan.get_status()
    assert s["running"] is False and s["stage"] == "failed"


class _FakePopen:
    calls = []
    def __init__(self, *a, **k):
        _FakePopen.calls.append((a, k)); self.pid = 4242


def test_start_guard_blocks_duplicate(tmp_path, monkeypatch):
    _FakePopen.calls = []
    monkeypatch.setattr(scan, "scan_running", lambda: (True, [999]))
    import subprocess as _sp
    monkeypatch.setattr(_sp, "Popen", _FakePopen)
    r = scan.start_scan()
    assert r["started"] is False and r["reason"] == "already_running"
    assert _FakePopen.calls == []  # never launched a second scan


def test_start_launches_when_idle(tmp_path, monkeypatch):
    _FakePopen.calls = []
    monkeypatch.setattr(scan, "scan_running", lambda: (False, []))
    monkeypatch.setattr(scan, "REPORTS", tmp_path)
    monkeypatch.setattr(scan, "STATE", tmp_path / "scan_state.json")
    monkeypatch.setattr(scan, "PIDFILE", tmp_path / "scan.pid")
    monkeypatch.setattr(scan, "RUNLOG", tmp_path / "run.log")
    import subprocess as _sp
    monkeypatch.setattr(_sp, "Popen", _FakePopen)
    r = scan.start_scan()
    assert r["started"] is True and r["pid"] == 4242 and len(_FakePopen.calls) == 1
    assert (tmp_path / "scan.pid").read_text() == "4242"
    assert json.loads((tmp_path / "scan_state.json").read_text())["source"] == "web"


def test_scan_endpoints_via_api(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(scan, "scan_running", lambda: (True, [999]))
    c = TestClient(app)
    s = c.get("/api/scan/status")
    assert s.status_code == 200
    body = s.json()
    assert "running" in body and "stage" in body and body["running"] is True
    r = c.post("/api/scan/start")
    assert r.status_code == 200
    assert r.json()["started"] is False and r.json()["reason"] == "already_running"
