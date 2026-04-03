#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH_ROOT = ROOT / "openwebui-patches" / "src"
CACHE_DIR = ROOT / "state" / "open-webui-source"
BUILD_DIR = ROOT / "state" / "open-webui-build"
DEFAULT_REPO = os.getenv("HERMES_OPENWEBUI_REPO", "https://github.com/open-webui/open-webui.git")
DEFAULT_REF = os.getenv("HERMES_OPENWEBUI_REF", "v0.8.12")
DEFAULT_IMAGE = os.getenv("HERMES_WEBUI_PATCHED_IMAGE", f"hermes-openwebui-patched:{DEFAULT_REF}")
EXCLUDES = {".git", "node_modules", ".venv", "backend/data", "build", ".svelte-kit", ".pytest_cache", "__pycache__"}


def log(message: str) -> None:
    print(f"[build-patched-openwebui] {message}", flush=True)


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_wsl() -> bool:
    return not is_windows() and (
        "WSL_DISTRO_NAME" in os.environ
        or "WSL_INTEROP" in os.environ
        or "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    )


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


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    log("+ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check, text=True, capture_output=capture)


def sync_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        if item.name in EXCLUDES:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(*EXCLUDES), dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def ensure_source(repo: str, ref: str) -> None:
    CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
    if not CACHE_DIR.exists():
        run(["git", "clone", repo, str(CACHE_DIR)])
    run(["git", "fetch", "--tags", "origin"], cwd=CACHE_DIR)
    run(["git", "checkout", ref], cwd=CACHE_DIR)
    run(["git", "reset", "--hard", ref], cwd=CACHE_DIR)


def apply_patch_overlay() -> None:
    if not PATCH_ROOT.exists():
        raise SystemExit(f"Missing patch tree: {PATCH_ROOT}")
    src_root = BUILD_DIR / "src"
    src_root.mkdir(parents=True, exist_ok=True)
    for item in PATCH_ROOT.rglob("*"):
        rel = item.relative_to(PATCH_ROOT)
        target = src_root / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def image_exists(image: str) -> bool:
    completed = run([docker_cmd(), "image", "inspect", image], check=False, capture=True)
    return completed.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a patched Open WebUI image with Hermes chat UI overlays")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--force", action="store_true", help="Rebuild even if the target image already exists")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if image_exists(args.image) and not args.force:
        log(f"Image already exists: {args.image}")
        return 0

    ensure_source(args.repo, args.ref)
    log(f"Preparing build tree from {CACHE_DIR}")
    sync_tree(CACHE_DIR, BUILD_DIR)
    log("Applying Hermes Open WebUI patch overlay")
    apply_patch_overlay()
    run([docker_cmd(), "build", "-t", args.image, "."], cwd=BUILD_DIR)
    log(f"Built patched Open WebUI image: {args.image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
