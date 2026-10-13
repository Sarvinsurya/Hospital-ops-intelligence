#!/usr/bin/env python3
"""
Hospital Operations Intelligence System — cross-platform launcher.

Works on Windows and macOS/Linux. It will:
  1. Detect the operating system.
  2. Ensure prerequisites (Python 3.12 venv, pip deps, npm deps, Ollama model).
  3. Build the SQLite warehouse if missing.
  4. Start the FastAPI backend (port 8077) and the Vite frontend (port 5190).
  5. Run post-launch health checks on both.
  6. Print the navigation links and open the UI in the browser.

Usage:
    python launch.py              # install (if needed) + run
    python launch.py --no-install # skip dependency checks, just run
    python launch.py --no-open    # don't auto-open the browser
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

BACKEND_PORT = 8077
FRONTEND_PORT = 5190
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"

IS_WINDOWS = platform.system() == "Windows"
C = {
    "g": "" if IS_WINDOWS else "\033[92m",
    "y": "" if IS_WINDOWS else "\033[93m",
    "r": "" if IS_WINDOWS else "\033[91m",
    "b": "" if IS_WINDOWS else "\033[96m",
    "d": "" if IS_WINDOWS else "\033[2m",
    "x": "" if IS_WINDOWS else "\033[0m",
}


def log(msg, color="x"):
    print(f"{C.get(color, '')}{msg}{C['x']}", flush=True)


def step(n, total, msg):
    log(f"\n[{n}/{total}] {msg}", "b")


# --------------------------------------------------------------------------
# OS-specific paths
# --------------------------------------------------------------------------
def venv_python() -> Path:
    return BACKEND / "venv" / ("Scripts" if IS_WINDOWS else "bin") / ("python.exe" if IS_WINDOWS else "python")


def venv_uvicorn() -> Path:
    return BACKEND / "venv" / ("Scripts" if IS_WINDOWS else "bin") / ("uvicorn.exe" if IS_WINDOWS else "uvicorn")


def find_python312() -> str | None:
    """Find a Python 3.11/3.12/3.13 interpreter to create the venv."""
    candidates = (
        ["py -3.12", "py -3.11", "python", "python3"]
        if IS_WINDOWS else
        ["python3.12", "python3.11", "python3.13", "python3"]
    )
    for cand in candidates:
        exe = cand.split()[0]
        if shutil.which(exe):
            try:
                out = subprocess.run(cand.split() + ["--version"], capture_output=True, text=True)
                ver = (out.stdout + out.stderr).strip()
                if any(v in ver for v in ("3.11", "3.12", "3.13")):
                    return cand
            except Exception:
                continue
    return shutil.which("python") or shutil.which("python3")


# --------------------------------------------------------------------------
# health check helper
# --------------------------------------------------------------------------
def http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    # Try the given URL; if it targets 127.0.0.1 and fails, retry on localhost
    # (and vice-versa) because Vite may bind only one of them.
    urls = [url]
    if "127.0.0.1" in url:
        urls.append(url.replace("127.0.0.1", "localhost"))
    elif "localhost" in url:
        urls.append(url.replace("localhost", "127.0.0.1"))
    last = ""
    for u in urls:
        try:
            with urllib.request.urlopen(u, timeout=timeout) as r:
                body = r.read(300).decode(errors="replace")
                return (200 <= r.status < 300), body
        except urllib.error.URLError as e:
            last = str(e)
        except Exception as e:
            last = str(e)
    return False, last


def wait_for(url: str, label: str, attempts: int = 40, delay: float = 1.0) -> bool:
    for i in range(attempts):
        ok, _ = http_ok(url)
        if ok:
            log(f"    {label} is up.", "g")
            return True
        time.sleep(delay)
        if i % 5 == 4:
            log(f"    …waiting for {label} ({i + 1}s)", "d")
    log(f"    {label} did NOT come up in time.", "r")
    return False


# --------------------------------------------------------------------------
# dependency setup
# --------------------------------------------------------------------------
def ensure_backend_deps():
    vpy = venv_python()
    if not vpy.exists():
        py = find_python312()
        if not py:
            log("    No suitable Python (3.11-3.13) found. Install Python 3.12.", "r")
            sys.exit(1)
        log(f"    Creating virtualenv with: {py}", "d")
        subprocess.run(py.split() + ["-m", "venv", str(BACKEND / "venv")], check=True)
    log("    Installing backend requirements…", "d")
    subprocess.run([str(vpy), "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True)
    subprocess.run([str(vpy), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt"), "-q"], check=True)
    log("    Backend dependencies ready.", "g")


def ensure_frontend_deps():
    if not shutil.which("npm"):
        log("    npm not found. Install Node.js 18+ from https://nodejs.org", "r")
        sys.exit(1)
    if not (FRONTEND / "node_modules").exists():
        log("    Installing frontend dependencies (npm install)…", "d")
        subprocess.run(["npm", "install"], cwd=FRONTEND, check=True, shell=IS_WINDOWS)
    log("    Frontend dependencies ready.", "g")


def check_ollama():
    ok, body = http_ok(f"{OLLAMA_URL}/api/tags", timeout=3)
    if not ok:
        log(f"    ⚠ Ollama not reachable at {OLLAMA_URL}. The AI agent will be offline.", "y")
        log("      Start it with: ollama serve   (and: ollama pull qwen2.5:3b)", "y")
        return
    if OLLAMA_MODEL.split(":")[0] in body:
        log(f"    Ollama is running with {OLLAMA_MODEL}.", "g")
    else:
        log(f"    ⚠ Ollama running but model '{OLLAMA_MODEL}' missing. Run: ollama pull {OLLAMA_MODEL}", "y")


def ensure_warehouse():
    db = BACKEND / "data" / "warehouse" / "hospital_ops.db"
    if db.exists():
        log("    Warehouse already built.", "g")
        return
    log("    Building SQLite warehouse (ETL)…", "d")
    subprocess.run([str(venv_python()), "-m", "app.etl.build_warehouse"], cwd=BACKEND, check=True)
    log("    Warehouse built.", "g")


# --------------------------------------------------------------------------
# server startup
# --------------------------------------------------------------------------
def start_backend() -> subprocess.Popen:
    cmd = [str(venv_uvicorn()), "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)]
    if not venv_uvicorn().exists():  # fallback to module invocation
        cmd = [str(venv_python()), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)]
    return subprocess.Popen(cmd, cwd=BACKEND)


def start_frontend() -> subprocess.Popen:
    return subprocess.Popen(["npm", "run", "dev"], cwd=FRONTEND, shell=IS_WINDOWS)


def free_port(port: int):
    """Best-effort: kill any process already bound to the port."""
    try:
        if IS_WINDOWS:
            out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
            pids = {line.split()[-1] for line in out.splitlines() if f":{port}" in line and "LISTENING" in line}
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
        else:
            out = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True).stdout
            for pid in out.split():
                subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception:
        pass


# --------------------------------------------------------------------------
# post-launch checks
# --------------------------------------------------------------------------
def post_checks() -> bool:
    log("\n── Post-launch health checks ──────────────────────────────", "b")
    checks = [
        (f"http://127.0.0.1:{BACKEND_PORT}/api/health", "Backend /api/health"),
        (f"http://127.0.0.1:{BACKEND_PORT}/api/analytics/summary", "Analytics summary"),
        (f"http://127.0.0.1:{BACKEND_PORT}/api/ml/model/wait-time/meta", "ML wait-time model"),
        (f"http://127.0.0.1:{BACKEND_PORT}/api/agent/health", "AI agent"),
        (f"http://127.0.0.1:{FRONTEND_PORT}/", "Frontend (Vite)"),
        (f"http://127.0.0.1:{FRONTEND_PORT}/api/health", "Frontend → API proxy"),
    ]
    all_ok = True
    for url, label in checks:
        ok, _ = http_ok(url, timeout=5)
        mark = f"{C['g']}✓ PASS{C['x']}" if ok else f"{C['r']}✗ FAIL{C['x']}"
        print(f"    {mark}  {label}")
        if not ok and "agent" not in label.lower():
            all_ok = False
    return all_ok


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-install", action="store_true", help="skip dependency checks")
    ap.add_argument("--no-open", action="store_true", help="don't open the browser")
    args = ap.parse_args()

    log("=" * 62, "d")
    log("  Hospital Operations Intelligence System — Launcher", "b")
    log(f"  OS detected: {platform.system()} ({platform.machine()})", "x")
    log("=" * 62, "d")

    total = 6
    if not args.no_install:
        step(1, total, "Checking backend (Python) dependencies")
        ensure_backend_deps()
        step(2, total, "Checking frontend (Node) dependencies")
        ensure_frontend_deps()
        step(3, total, "Checking Ollama (local AI model)")
        check_ollama()
        step(4, total, "Ensuring data warehouse")
        ensure_warehouse()
    else:
        log("\nSkipping dependency checks (--no-install).", "y")

    step(5, total, "Starting servers")
    free_port(BACKEND_PORT)
    free_port(FRONTEND_PORT)
    backend = start_backend()
    frontend = start_frontend()
    log("    Launched backend + frontend processes.", "d")

    be = wait_for(f"http://127.0.0.1:{BACKEND_PORT}/api/health", "Backend")
    fe = wait_for(f"http://127.0.0.1:{FRONTEND_PORT}/", "Frontend")

    step(6, total, "Running post-checks")
    ok = post_checks() if (be and fe) else False

    log("\n" + "=" * 62, "d")
    if ok:
        log("  ✅  ALL SYSTEMS GO", "g")
    else:
        log("  ⚠  Some checks failed — see above. Servers are still running.", "y")
    log("=" * 62, "d")
    log(f"\n  🖥  Frontend (open this):  {C['g']}http://localhost:{FRONTEND_PORT}{C['x']}")
    log(f"  🔌  Backend API:          http://localhost:{BACKEND_PORT}")
    log(f"  📚  API docs (Swagger):   http://localhost:{BACKEND_PORT}/docs")
    log("\n  Press Ctrl+C to stop both servers.\n", "d")

    if not args.no_open:
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
        except Exception:
            pass

    # keep running until Ctrl+C, then shut both down
    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                log("Backend process exited.", "r"); break
            if frontend.poll() is not None:
                log("Frontend process exited.", "r"); break
    except KeyboardInterrupt:
        log("\nShutting down…", "y")
    finally:
        for p in (frontend, backend):
            try:
                p.terminate()
            except Exception:
                pass
        free_port(BACKEND_PORT)
        free_port(FRONTEND_PORT)
        log("Stopped.", "g")


if __name__ == "__main__":
    main()
