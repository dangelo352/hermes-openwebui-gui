from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
STATE_DIR = ROOT_DIR / "state"
OPEN_WEBUI_DATA_DIR = ROOT_DIR / "open-webui-data"
VENV_DIR = ROOT_DIR / ".venv"
ADAPTER_LOG = STATE_DIR / "adapter.log"
ADAPTER_PID = STATE_DIR / "adapter.pid"
DEFAULT_MODEL = os.getenv("HERMES_OPENAI_MODEL", "hermes-gui")
DEFAULT_API_KEY = os.getenv("HERMES_OPENAI_API_KEY", "hermes-local")
ADAPTER_PORT = int(os.getenv("HERMES_ADAPTER_PORT", "8001"))
WEBUI_PORT = int(os.getenv("HERMES_WEBUI_PORT", "8080"))
WEBUI_CONTAINER = os.getenv("HERMES_WEBUI_CONTAINER", "hermes-open-webui")
WEBUI_IMAGE = os.getenv("HERMES_WEBUI_IMAGE", "ghcr.io/open-webui/open-webui:main")


def log(message: str) -> None:
    print(f"[launcher] {message}", flush=True)


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_macos() -> bool:
    return sys.platform == "darwin"


def state_init() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OPEN_WEBUI_DATA_DIR.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], check: bool = True, capture: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture, cwd=ROOT_DIR, env=env)


def background(cmd: list[str], env: dict[str, str]) -> int:
    with ADAPTER_LOG.open("a", encoding="utf-8") as fh:
        process = subprocess.Popen(
            cmd,
            cwd=ROOT_DIR,
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    ADAPTER_PID.write_text(str(process.pid), encoding="utf-8")
    return process.pid


def venv_python() -> Path:
    if is_windows():
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def find_python() -> str:
    candidates = []
    if is_windows():
        candidates.extend([["py", "-3.11"], ["py", "-3"], ["python"]])
    else:
        candidates.extend([["python3.11"], ["python3"], ["python"]])
    for cmd in candidates:
        try:
            completed = subprocess.run(cmd + ["--version"], capture_output=True, text=True, check=True)
            if completed.stdout or completed.stderr:
                return cmd[0] if len(cmd) == 1 else " ".join(cmd)
        except Exception:
            continue
    raise SystemExit("Python 3 is required but was not found.")


def python_cmd_args(spec: str) -> list[str]:
    return spec.split()


def ensure_venv() -> None:
    if venv_python().exists():
        return
    spec = find_python()
    log(f"Creating virtual environment with {spec}")
    run(python_cmd_args(spec) + ["-m", "venv", str(VENV_DIR)])


def ensure_requirements() -> None:
    python = str(venv_python())
    log("Installing adapter dependencies")
    run([python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    run([python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)


def hermes_candidates() -> list[Path]:
    home = Path.home()
    candidates = [
        home / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
        home / ".hermes" / "hermes-agent" / "venv" / "Scripts" / "hermes.exe",
        home / ".hermes" / "bin" / "hermes",
        home / ".local" / "bin" / "hermes",
    ]
    found = shutil.which("hermes")
    if found:
        candidates.insert(0, Path(found))
    return candidates


def detect_hermes() -> tuple[str, str]:
    hermes_bin = os.getenv("HERMES_BIN")
    if not hermes_bin:
        for candidate in hermes_candidates():
            if candidate.exists():
                hermes_bin = str(candidate)
                break
    if not hermes_bin:
        raise SystemExit(
            "Hermes CLI was not found. Set HERMES_BIN or install Hermes in ~/.hermes/hermes-agent/venv."
        )

    hermes_workdir = os.getenv("HERMES_WORKDIR")
    if not hermes_workdir:
        bin_path = Path(hermes_bin).expanduser()
        for parent in [bin_path.parent, *bin_path.parents]:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                hermes_workdir = str(parent)
                break
    if not hermes_workdir:
        fallback = Path.home() / ".hermes" / "hermes-agent"
        hermes_workdir = str(fallback if fallback.exists() else ROOT_DIR)
    return hermes_bin, hermes_workdir


def wait_http(url: str, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(1)
    raise SystemExit(f"Timed out waiting for {url}")


def adapter_running() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{ADAPTER_PORT}/health", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def read_pid() -> int | None:
    if not ADAPTER_PID.exists():
        return None
    try:
        return int(ADAPTER_PID.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def kill_pid(pid: int) -> None:
    if is_windows():
        subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], check=False, capture_output=True, text=True)
    else:
        os.kill(pid, signal.SIGTERM)


def start_adapter() -> None:
    if adapter_running():
        log(f"Adapter already running on http://127.0.0.1:{ADAPTER_PORT}")
        return
    hermes_bin, hermes_workdir = detect_hermes()
    env = os.environ.copy()
    env.update(
        {
            "HERMES_BIN": hermes_bin,
            "HERMES_WORKDIR": hermes_workdir,
            "HERMES_OPENAI_MODEL": DEFAULT_MODEL,
            "HERMES_OPENAI_API_KEY": DEFAULT_API_KEY,
            "HERMES_ADAPTER_STATE_DIR": str(STATE_DIR),
        }
    )
    python = str(venv_python())
    cmd = [python, "-m", "uvicorn", "adapter.app:app", "--host", "0.0.0.0", "--port", str(ADAPTER_PORT)]
    pid = background(cmd, env)
    log(f"Started adapter with PID {pid}")
    wait_http(f"http://127.0.0.1:{ADAPTER_PORT}/health", timeout=60)


def docker_cmd() -> str:
    found = shutil.which("docker")
    if found:
        return found
    if is_windows():
        docker_exe = Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe")
        if docker_exe.exists():
            return str(docker_exe)
    raise SystemExit("Docker is required but was not found in PATH.")


def start_docker_desktop() -> None:
    if is_windows():
        docker_desktop = Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")
        if docker_desktop.exists():
            subprocess.Popen([str(docker_desktop)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif is_macos():
        docker_app = Path("/Applications/Docker.app")
        if docker_app.exists():
            subprocess.Popen(["open", "-a", "Docker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_docker(timeout: int = 120) -> None:
    start_docker_desktop()
    cmd = docker_cmd()
    deadline = time.time() + timeout
    while time.time() < deadline:
        completed = subprocess.run([cmd, "info"], check=False, capture_output=True, text=True)
        if completed.returncode == 0:
            return
        time.sleep(3)
    raise SystemExit("Docker did not become ready in time.")


def docker_host_args() -> list[str]:
    if is_windows() or is_macos():
        return []
    return ["--add-host=host.docker.internal:host-gateway"]


def start_openwebui() -> None:
    cmd = docker_cmd()
    wait_docker()
    subprocess.run([cmd, "rm", "-f", WEBUI_CONTAINER], check=False, capture_output=True, text=True)
    run_cmd = [
        cmd,
        "run",
        "-d",
        "-p",
        f"{WEBUI_PORT}:8080",
        "-e",
        "ENABLE_OPENAI_API=True",
        "-e",
        "ENABLE_FORWARD_USER_INFO_HEADERS=True",
        "-e",
        f"OPENAI_API_BASE_URL=http://host.docker.internal:{ADAPTER_PORT}/v1",
        "-e",
        f"OPENAI_API_KEY={DEFAULT_API_KEY}",
        "-e",
        "WEBUI_AUTH=False",
        "-v",
        f"{OPEN_WEBUI_DATA_DIR.resolve()}:/app/backend/data",
        "--name",
        WEBUI_CONTAINER,
        "--restart",
        "unless-stopped",
        *docker_host_args(),
        WEBUI_IMAGE,
    ]
    run(run_cmd)


def stop_openwebui() -> None:
    try:
        cmd = docker_cmd()
    except SystemExit:
        return
    subprocess.run([cmd, "rm", "-f", WEBUI_CONTAINER], check=False, capture_output=True, text=True)


def stop_adapter() -> None:
    pid = read_pid()
    if pid:
        try:
            kill_pid(pid)
        except Exception:
            pass
        ADAPTER_PID.unlink(missing_ok=True)


def status() -> None:
    result = {
        "adapter_url": f"http://127.0.0.1:{ADAPTER_PORT}",
        "adapter_running": adapter_running(),
        "adapter_pid": read_pid(),
        "webui_url": f"http://127.0.0.1:{WEBUI_PORT}",
    }
    try:
        cmd = docker_cmd()
        completed = subprocess.run([cmd, "ps", "--filter", f"name={WEBUI_CONTAINER}", "--format", "{{.Names}}"], check=False, capture_output=True, text=True)
        result["webui_running"] = WEBUI_CONTAINER in completed.stdout.splitlines()
    except SystemExit:
        result["webui_running"] = False
    print(json.dumps(result, indent=2))


def start(open_browser: bool = True) -> None:
    state_init()
    ensure_venv()
    ensure_requirements()
    start_adapter()
    start_openwebui()
    log(f"Open WebUI ready at http://127.0.0.1:{WEBUI_PORT}")
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{WEBUI_PORT}")


def stop() -> None:
    stop_openwebui()
    stop_adapter()
    log("Stopped Hermes adapter and Open WebUI")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-platform Hermes + Open WebUI launcher")
    parser.add_argument("command", nargs="?", default="start", choices=["start", "stop", "restart", "status"])
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after startup")
    args = parser.parse_args()

    if args.command == "start":
        start(open_browser=not args.no_browser)
    elif args.command == "stop":
        stop()
    elif args.command == "restart":
        stop()
        start(open_browser=not args.no_browser)
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
