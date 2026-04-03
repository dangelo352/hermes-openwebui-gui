from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
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
BUILD_PATCHED_WEBUI_SCRIPT = ROOT_DIR / "scripts" / "build_patched_openwebui.py"
INSTALL_WORKSPACE_ASSETS_SCRIPT = ROOT_DIR / "scripts" / "install_openwebui_workspace_assets.py"

DEFAULT_MODEL = os.getenv("HERMES_OPENAI_MODEL", "hermes-gui")
DEFAULT_API_KEY = os.getenv("HERMES_OPENAI_API_KEY", "hermes-local")
ADAPTER_PORT = int(os.getenv("HERMES_ADAPTER_PORT", "8001"))
WEBUI_PORT = int(os.getenv("HERMES_WEBUI_PORT", "8080"))
WEBUI_CONTAINER = os.getenv("HERMES_WEBUI_CONTAINER", "hermes-open-webui")
WEBUI_UPSTREAM_IMAGE = os.getenv("HERMES_WEBUI_IMAGE", "ghcr.io/open-webui/open-webui:main")
OPENWEBUI_REF = os.getenv("HERMES_OPENWEBUI_REF", "v0.8.12")
PATCHED_WEBUI_IMAGE = os.getenv("HERMES_WEBUI_PATCHED_IMAGE", f"hermes-openwebui-patched:{OPENWEBUI_REF}")
USE_PATCHED_WEBUI = os.getenv("HERMES_WEBUI_USE_PATCHED", "true").strip().lower() not in {"0", "false", "no", "off"}
WEBUI_AUTH = os.getenv("WEBUI_AUTH", "False")


def log(message: str) -> None:
    print(f"[launcher] {message}", flush=True)


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_wsl() -> bool:
    return not is_windows() and (
        "WSL_DISTRO_NAME" in os.environ
        or "WSL_INTEROP" in os.environ
        or "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    )


def state_init() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OPEN_WEBUI_DATA_DIR.mkdir(parents=True, exist_ok=True)


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
        cwd=str(cwd or ROOT_DIR),
        env=env,
    )


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


def detect_host_python() -> list[str]:
    candidates: list[list[str]] = []
    if is_windows():
        candidates.extend([["py", "-3.11"], ["py", "-3"], ["python"]])
    else:
        candidates.extend([["python3.11"], ["python3"], ["python"]])
    for cmd in candidates:
        try:
            completed = subprocess.run(cmd + ["--version"], check=True, capture_output=True, text=True)
            if completed.returncode == 0:
                return cmd
        except Exception:
            continue
    raise SystemExit("Python 3 is required but was not found.")


def venv_has_pip() -> bool:
    python = venv_python()
    if not python.exists():
        return False
    completed = subprocess.run([str(python), "-m", "pip", "--version"], check=False, capture_output=True, text=True)
    return completed.returncode == 0


def ensure_venv() -> None:
    if venv_python().exists() and venv_has_pip():
        return
    if VENV_DIR.exists():
        log("Recreating broken virtual environment")
        shutil.rmtree(VENV_DIR)
    host_python = detect_host_python()
    log(f"Creating virtual environment with {' '.join(host_python)}")
    run(host_python + ["-m", "venv", str(VENV_DIR)])


def ensure_requirements() -> None:
    ensure_venv()
    python = str(venv_python())
    log("Installing adapter dependencies")
    run([python, "-m", "pip", "install", "--upgrade", "pip"])
    run([python, "-m", "pip", "install", "-r", "requirements.txt"])


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
        raise SystemExit("Hermes CLI was not found. Set HERMES_BIN or install Hermes in ~/.hermes/hermes-agent/venv.")

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


def ensure_launcher_ready() -> tuple[str, str]:
    state_init()
    ensure_requirements()
    hermes_bin, hermes_workdir = detect_hermes()
    return hermes_bin, hermes_workdir


def start_adapter() -> None:
    if adapter_running():
        log(f"Adapter already running on http://127.0.0.1:{ADAPTER_PORT}")
        return
    hermes_bin, hermes_workdir = ensure_launcher_ready()
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


def docker_candidates() -> list[str]:
    env_value = os.getenv("HERMES_DOCKER_BIN")
    candidates: list[str] = []
    if env_value:
        candidates.append(env_value)

    found = shutil.which("docker")
    if found:
        candidates.append(found)

    if is_windows():
        candidates.extend(
            [
                "C:/Program Files/Docker/Docker/resources/bin/docker.exe",
                "C:/Program Files/Docker/Docker/resources/bin/docker",
            ]
        )
    elif is_wsl():
        candidates.extend(
            [
                "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe",
                "/mnt/c/Program Files/Docker/Docker/resources/bin/docker",
            ]
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def docker_cmd() -> str:
    for candidate in docker_candidates():
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise SystemExit(
        "Docker is required but was not found. Install Docker Desktop/Docker Engine or set HERMES_DOCKER_BIN."
    )


def start_docker_desktop() -> None:
    if is_windows():
        docker_desktop = Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")
        if docker_desktop.exists():
            subprocess.Popen([str(docker_desktop)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif is_macos():
        docker_app = Path("/Applications/Docker.app")
        if docker_app.exists():
            subprocess.Popen(["open", "-a", "Docker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif is_wsl():
        cmd_exe = shutil.which("cmd.exe") or "/mnt/c/WINDOWS/system32/cmd.exe"
        if Path(cmd_exe).exists() or shutil.which("cmd.exe"):
            subprocess.Popen(
                [cmd_exe, "/c", "start", "", "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


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
    if is_windows() or is_macos() or is_wsl():
        return []
    return ["--add-host=host.docker.internal:host-gateway"]


def image_exists(image: str) -> bool:
    cmd = docker_cmd()
    completed = subprocess.run([cmd, "image", "inspect", image], check=False, capture_output=True, text=True)
    return completed.returncode == 0


def desired_webui_image() -> str:
    return PATCHED_WEBUI_IMAGE if USE_PATCHED_WEBUI else WEBUI_UPSTREAM_IMAGE


def ensure_webui_image() -> str:
    image = desired_webui_image()
    if image_exists(image):
        return image
    if not USE_PATCHED_WEBUI:
        return image
    if not BUILD_PATCHED_WEBUI_SCRIPT.exists():
        raise SystemExit(f"Patched Open WebUI builder missing: {BUILD_PATCHED_WEBUI_SCRIPT}")
    log(f"Building patched Open WebUI image: {image}")
    run([sys.executable, str(BUILD_PATCHED_WEBUI_SCRIPT), "--image", image])
    if not image_exists(image):
        raise SystemExit(f"Patched Open WebUI image was not created: {image}")
    return image


def install_workspace_assets() -> None:
    ensure_launcher_ready()
    if not INSTALL_WORKSPACE_ASSETS_SCRIPT.exists():
        log("Workspace asset installer not found; skipping")
        return
    run([str(venv_python()), str(INSTALL_WORKSPACE_ASSETS_SCRIPT)])


def start_openwebui() -> None:
    ensure_launcher_ready()
    cmd = docker_cmd()
    wait_docker()
    image = ensure_webui_image()
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
        f"WEBUI_AUTH={WEBUI_AUTH}",
        "-v",
        f"{OPEN_WEBUI_DATA_DIR.resolve()}:/app/backend/data",
        "--name",
        WEBUI_CONTAINER,
        "--restart",
        "unless-stopped",
        *docker_host_args(),
        image,
    ]
    run(run_cmd)
    wait_http(f"http://127.0.0.1:{WEBUI_PORT}/health", timeout=120)
    install_workspace_assets()


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


def prepare() -> None:
    hermes_bin, hermes_workdir = ensure_launcher_ready()
    summary = {
        "root_dir": str(ROOT_DIR),
        "venv_python": str(venv_python()),
        "hermes_bin": hermes_bin,
        "hermes_workdir": hermes_workdir,
        "docker_bin": docker_cmd() if any(Path(c).exists() or shutil.which(c) for c in docker_candidates()) else None,
        "adapter_url": f"http://127.0.0.1:{ADAPTER_PORT}",
        "webui_url": f"http://127.0.0.1:{WEBUI_PORT}",
        "patched_webui_enabled": USE_PATCHED_WEBUI,
    }
    print(json.dumps(summary, indent=2))


def status() -> None:
    image = desired_webui_image()
    result = {
        "adapter_url": f"http://127.0.0.1:{ADAPTER_PORT}",
        "adapter_running": adapter_running(),
        "adapter_pid": read_pid(),
        "webui_url": f"http://127.0.0.1:{WEBUI_PORT}",
        "webui_image": image,
        "webui_image_present": False,
        "patched_webui_enabled": USE_PATCHED_WEBUI,
        "docker_bin": None,
    }
    try:
        cmd = docker_cmd()
        result["docker_bin"] = cmd
        result["webui_image_present"] = image_exists(image)
        completed = subprocess.run([cmd, "ps", "--filter", f"name={WEBUI_CONTAINER}", "--format", "{{.Names}}"], check=False, capture_output=True, text=True)
        result["webui_running"] = WEBUI_CONTAINER in completed.stdout.splitlines()
    except SystemExit:
        result["webui_running"] = False
    print(json.dumps(result, indent=2))


def build_webui(force: bool = False) -> None:
    wait_docker()
    if not BUILD_PATCHED_WEBUI_SCRIPT.exists():
        raise SystemExit(f"Patched Open WebUI builder missing: {BUILD_PATCHED_WEBUI_SCRIPT}")
    cmd = [sys.executable, str(BUILD_PATCHED_WEBUI_SCRIPT), "--image", PATCHED_WEBUI_IMAGE]
    if force:
        cmd.append("--force")
    run(cmd)


def git_pull_ff_only() -> None:
    if not (ROOT_DIR / ".git").exists():
        log("No git repository found here; skipping git pull")
        return
    log("Running git pull --ff-only")
    run(["git", "pull", "--ff-only"])


def start(open_browser: bool = True) -> None:
    ensure_launcher_ready()
    start_adapter()
    start_openwebui()
    log(f"Open WebUI ready at http://127.0.0.1:{WEBUI_PORT}")
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{WEBUI_PORT}")


def stop() -> None:
    stop_openwebui()
    stop_adapter()
    log("Stopped Hermes adapter and Open WebUI")


def update(open_browser: bool = True, skip_git_pull: bool = False) -> None:
    if not skip_git_pull:
        git_pull_ff_only()
    if USE_PATCHED_WEBUI:
        build_webui(force=True)
    start(open_browser=open_browser)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-platform Hermes + Open WebUI launcher")
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=[
            "start",
            "stop",
            "restart",
            "status",
            "prepare",
            "start-adapter",
            "start-webui",
            "install-workspace-assets",
            "build-webui",
            "rebuild-webui",
            "update",
        ],
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after startup")
    parser.add_argument("--skip-git-pull", action="store_true", help="For update: skip git pull and only rebuild/restart")
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
    elif args.command == "prepare":
        prepare()
    elif args.command == "start-adapter":
        start_adapter()
    elif args.command == "start-webui":
        start_openwebui()
    elif args.command == "install-workspace-assets":
        install_workspace_assets()
    elif args.command == "build-webui":
        build_webui(force=False)
    elif args.command == "rebuild-webui":
        build_webui(force=True)
    elif args.command == "update":
        update(open_browser=not args.no_browser, skip_git_pull=args.skip_git_pull)


if __name__ == "__main__":
    main()
