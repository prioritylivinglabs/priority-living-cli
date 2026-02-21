#!/usr/bin/env python3
"""Priority Living CLI — Bridge worker (poll/stream/result executor)."""

import json
import os
import platform
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from priority_living import __version__
from priority_living.config_manager import load_config
from priority_living.error_reporter import report_error
from priority_living.offline_queue import resilient_request, try_drain_queue

BANNER = """
╔═══════════════════════════════════════════╗
║     Priority Living CLI  v""" + __version__ + """          ║
║     Bridge Worker — Local Executor        ║
╚═══════════════════════════════════════════╝
"""

MAX_OUTPUT_CHARS = 50000
DANGEROUS_COMMANDS = [
    "rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "fork bomb",
    "format c:", "del /f /s /q", "shutdown", "reboot",
]

running = True
session_id = None
machine_name = platform.node() or "unknown"

def signal_handler(sig, frame):
    global running
    print("\n🛑 Shutting down gracefully...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def api_request(endpoint, data=None, method="GET", api_key="", backend="", anon_key=""):
    url = f"{backend}/functions/v1/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "x-bridge-key": api_key,
    }
    if data:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  ⚠ API error {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  ⚠ Request failed: {e}")
        return None


def is_dangerous(cmd):
    lower = cmd.lower().strip()
    return any(d in lower for d in DANGEROUS_COMMANDS)


def execute_command(cmd, stream_callback=None):
    if is_dangerous(cmd):
        return {"exit_code": 1, "output": "🚫 Command blocked: potentially dangerous operation."}
    try:
        process = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            cwd=str(Path.home()),
        )
        output_lines = []
        for line in iter(process.stdout.readline, ""):
            output_lines.append(line)
            if stream_callback:
                stream_callback(line)
            total = sum(len(l) for l in output_lines)
            if total > MAX_OUTPUT_CHARS:
                output_lines.append("\n... [output truncated] ...")
                process.kill()
                break
        process.wait(timeout=300)
        return {"exit_code": process.returncode, "output": "".join(output_lines)}
    except subprocess.TimeoutExpired:
        process.kill()
        return {"exit_code": -1, "output": "⏱ Command timed out (5 min limit)."}
    except Exception as e:
        return {"exit_code": -1, "output": f"❌ Execution error: {e}"}


def send_heartbeat(api_key, backend, anon_key, uptime_start):
    """Send heartbeat to bridge-status endpoint."""
    import shutil
    try:
        gpu_available = False
        gpu_name = None
        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(0)
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                gpu_available = True
                gpu_name = "Apple Silicon (MPS)"
        except ImportError:
            pass

        disk = shutil.disk_usage(str(Path.home()))
        disk_free_gb = round(disk.free / (1024**3), 1)

        api_request(
            "bridge-status",
            data={
                "machine_name": machine_name,
                "cli_version": __version__,
                "gpu_available": gpu_available,
                "gpu_name": gpu_name,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "installed_models": _get_installed_models(),
                "uptime_seconds": int(time.time() - uptime_start),
                "os_info": f"{platform.system()} {platform.release()}",
                "disk_free_gb": disk_free_gb,
            },
            method="POST",
            api_key=api_key,
            backend=backend,
            anon_key=anon_key,
        )
    except Exception:
        pass  # heartbeat failures are non-fatal


def _get_installed_models():
    """List models in ~/.priority-living/models/"""
    models_dir = Path.home() / ".priority-living" / "models"
    if not models_dir.exists():
        return []
    return [d.name for d in models_dir.iterdir() if d.is_dir()]


def poll_loop(api_key, backend, anon_key, poll_interval, auto_restart):
    global running, session_id
    backoff = 1
    consecutive_errors = 0
    uptime_start = time.time()
    last_heartbeat = 0

    print(f"🔗 Backend:  {backend}")
    print(f"🖥  Machine:  {machine_name}")
    print(f"⏱  Polling:  every {poll_interval}s")
    print(f"🔄 Auto-restart: {'yes' if auto_restart else 'no'}")
    print()

    while running:
        try:
            # Drain offline queue on each cycle
            try_drain_queue(api_key, backend, anon_key)

            # Send heartbeat every 60s
            now = time.time()
            if now - last_heartbeat > 60:
                send_heartbeat(api_key, backend, anon_key, uptime_start)
                last_heartbeat = now

            result = api_request(
                "bridge-poll",
                data={
                    "machine_name": machine_name,
                    "session_id": session_id,
                    "capabilities": ["execute", "file_transfer", "stream"],
                },
                method="POST", api_key=api_key, backend=backend, anon_key=anon_key,
            )

            if result is None:
                consecutive_errors += 1
                if consecutive_errors > 10:
                    backoff = min(backoff * 2, 60)
                    print(f"  ⏳ Backing off: {backoff}s")
                time.sleep(backoff)
                continue

            consecutive_errors = 0
            backoff = 1

            if result.get("session_id"):
                session_id = result["session_id"]

            command = result.get("command")
            command_id = result.get("command_id")

            if command and command_id:
                print(f"📥 Received: {command[:80]}{'...' if len(command) > 80 else ''}")

                def stream_chunk(line):
                    resilient_request(
                        "bridge-stream",
                        data={"command_id": command_id, "chunk": line, "machine_name": machine_name},
                        method="POST", api_key=api_key, backend=backend, anon_key=anon_key,
                    )

                result_data = execute_command(command, stream_callback=stream_chunk)

                resilient_request(
                    "bridge-result",
                    data={
                        "command_id": command_id,
                        "exit_code": result_data["exit_code"],
                        "output": result_data["output"],
                        "machine_name": machine_name,
                    },
                    method="POST", api_key=api_key, backend=backend, anon_key=anon_key,
                )

                status = "✅" if result_data["exit_code"] == 0 else "❌"
                print(f"  {status} Exit code: {result_data['exit_code']}")

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"  ⚠ Loop error: {e}")
            report_error(e, api_key, backend, anon_key)
            time.sleep(5)

    print("👋 Worker stopped.")


def handle_bridge(args, default_backend, default_anon_key):
    print(BANNER)
    cfg = load_config()

    if not args.bridge_action or args.bridge_action == "start":
        api_key = args.key or cfg.get("bridge_key")
        if not api_key:
            print("❌ Bridge key required. Use --key pb_xxx or: pl config set bridge_key pb_xxx")
            sys.exit(1)
        if not api_key.startswith("pb_"):
            print("❌ Invalid bridge key. Must start with 'pb_'")
            sys.exit(1)

        global machine_name
        machine_name = args.name or cfg.get("machine_name", platform.node() or "unknown")
        backend = cfg.get("backend_url", default_backend)
        anon_key = cfg.get("anon_key", default_anon_key)
        poll_interval = args.poll_interval or cfg.get("poll_interval", 3)

        while True:
            try:
                poll_loop(api_key, backend, anon_key, poll_interval, args.auto_restart)
                if not args.auto_restart or not running:
                    break
                print("🔄 Restarting in 5s...")
                time.sleep(5)
            except Exception as e:
                print(f"💥 Fatal error: {e}")
                report_error(e, api_key, backend, anon_key)
                if not args.auto_restart:
                    break
                print("🔄 Restarting in 10s...")
                time.sleep(10)
    else:
        print(f"Unknown bridge action: {args.bridge_action}")
