"""Scan Market control for the website.

POST /api/scan/start launches scripts/weekly_run.py as a detached
subprocess; GET /api/scan/status derives live progress from the pipeline's
own files (stage-1 checkpoint + latest report) and the process list, so it
also sees scans started outside the website (terminal / Monday cron).
"""
import json, math, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "data" / "reports"
STATE = REPORTS / "scan_state.json"          # written when the website starts a scan
PIDFILE = REPORTS / "scan.pid"               # pid of the website-started scan
RUNLOG = REPORTS / "run.log"
LATEST = REPORTS / "latest.json"
CKPT = REPORTS / "stage1_checkpoint.json"
BATCH = 100  # pipeline.stage1 batch size

_TOTAL_BATCHES = None


def _read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def total_batches():
    """ceil(universe listings / batch size) — 80 for the ~7,987 universe."""
    global _TOTAL_BATCHES
    if _TOTAL_BATCHES is None:
        try:
            from app import universe as u
            _TOTAL_BATCHES = math.ceil(u.load_universe()["counts"]["total"] / BATCH)
        except Exception:
            _TOTAL_BATCHES = 80
    return _TOTAL_BATCHES


def find_scan_pids():
    """PIDs of any running weekly_run.py process, whoever started it."""
    pids = []
    proc = Path("/proc")
    if not proc.exists():
        return pids
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
        except Exception:
            continue
        if "weekly_run.py" in cmd and "python" in cmd:
            pids.append(int(entry.name))
    return pids


def _pid_alive(pid):
    pid = int(pid)
    if os.name == "nt":
        # NEVER os.kill(pid, 0) on Windows: signal 0 IS CTRL_C_EVENT there,
        # so the "check" sends Ctrl+C to the console process group and shuts
        # the web server itself down. Use the Win32 API instead.
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return False
                return code.value == 259  # STILL_ACTIVE
            finally:
                k32.CloseHandle(handle)
        except Exception:
            return False
    # A zombie (defunct) child still answers os.kill — treat it as dead,
    # otherwise a killed scan would block new scans forever.
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        if stat.rsplit(")", 1)[-1].split()[0] == "Z":
            return False
    except Exception:
        pass
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def scan_running():
    """(running, pids) — process list first, pid file as fallback."""
    pids = find_scan_pids()
    if pids:
        return True, pids
    try:
        pid = int(PIDFILE.read_text(encoding="utf-8").strip())
        if _pid_alive(pid):
            return True, [pid]
    except Exception:
        pass
    return False, []


def checkpoint_progress():
    """Stage-1 progress from the pipeline checkpoint, or None."""
    ck = _read_json(CKPT)
    if not ck:
        return None
    results = ck.get("results") or []
    return {
        "done_batches": len(ck.get("done_batches") or []),
        "total_batches": total_batches(),
        "results": len(results),
        "liquid": sum(1 for r in results if r.get("liquid")),
        "run_date": ck.get("run_date"),
    }


def _log_stage():
    """Last stage marker in the run log — disambiguates stage 2, when the
    stage-1 checkpoint has already been removed by the pipeline."""
    try:
        data = RUNLOG.read_bytes()[-200_000:].decode(errors="ignore")
    except Exception:
        return None
    i1, i2 = data.rfind("[stage1]"), data.rfind("[stage2]")
    if i1 == -1 and i2 == -1:
        return None
    return "stage2" if i2 > i1 else "stage1"


def _summary(report):
    return {
        "run_date": report.get("run_date"),
        "target_date": report.get("target_date"),
        "data_as_of": report.get("data_as_of"),
        "picks_count": len(report.get("picks") or []),
        "stage_counts": report.get("stage_counts"),
    }


def get_status():
    running, _pids = scan_running()
    state = _read_json(STATE) or {}
    started_at = state.get("started_at")
    prog = checkpoint_progress()
    out = {"running": running, "started_at": started_at, "stage1": prog, "summary": None}

    if running:
        if prog and prog["done_batches"] < prog["total_batches"]:
            out["stage"] = "stage1"
        elif prog:  # checkpoint complete -> deep evaluation
            out["stage"] = "stage2"
        else:  # checkpoint gone (stage 1 finished) or not written yet
            out["stage"] = _log_stage() or "stage1"
        return out

    latest = _read_json(LATEST)
    if latest is not None:
        newer = True
        if started_at and LATEST.exists():
            try:
                start_ts = datetime.fromisoformat(started_at).timestamp()
                newer = LATEST.stat().st_mtime >= start_ts
            except Exception:
                newer = True
        if newer:
            out["stage"] = "done"
            out["summary"] = _summary(latest)
            return out
    out["stage"] = "failed" if started_at else "idle"
    return out


def start_scan():
    running, pids = scan_running()
    if running:
        return {"started": False, "reason": "already_running", "running": True, "pids": pids}
    REPORTS.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps({"started_at": started_at, "source": "web"}), encoding="utf-8")
    log = open(RUNLOG, "ab")
    popen_kw = {}
    if os.name == "nt":
        # Fully detach the scan from the server's console on Windows so no
        # console control event can ever travel between the two processes.
        popen_kw["creationflags"] = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        )
        popen_kw["stdin"] = subprocess.DEVNULL
    else:
        popen_kw["start_new_session"] = True
    proc = subprocess.Popen(
        [sys.executable, "scripts/weekly_run.py"],
        cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
        **popen_kw,
    )
    PIDFILE.write_text(str(proc.pid), encoding="utf-8")
    return {"started": True, "started_at": started_at, "pid": proc.pid}
