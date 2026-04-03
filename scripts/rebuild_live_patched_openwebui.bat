@echo off
setlocal
wsl.exe -d Ubuntu bash -lc "cd /root/hermes-openwebui-gui && python3 scripts/rebuild_live_patched_openwebui.py"
