import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app import bhavcopy


def test_prune_raw_drops_files_older_than_the_window(tmp_path, monkeypatch):
    monkeypatch.setattr(bhavcopy, "RAW", tmp_path)
    old = date(2024, 1, 2)
    keep = date(2026, 10, 1)
    start = date(2025, 9, 12)
    for ex in ("nse", "bse"):
        folder = tmp_path / ex
        folder.mkdir()
        (folder / f"{old:%Y%m%d}.csv").write_text("old", encoding="utf-8")
        (folder / f"{keep:%Y%m%d}.csv").write_text("keep", encoding="utf-8")
        (folder / "missing.txt").write_text(f"{old:%Y%m%d}\n{keep:%Y%m%d}\njunk\n", encoding="utf-8")

    removed = bhavcopy.prune_raw(start, log=lambda *_a, **_k: None)

    assert removed == 2
    assert not (tmp_path / "nse" / f"{old:%Y%m%d}.csv").exists()
    assert (tmp_path / "bse" / f"{keep:%Y%m%d}.csv").exists()
    missing = (tmp_path / "nse" / "missing.txt").read_text(encoding="utf-8").splitlines()
    assert missing == [f"{keep:%Y%m%d}"]
