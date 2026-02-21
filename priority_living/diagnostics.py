"""Priority Living CLI — System diagnostics (status & diagnose)."""

import json
import os
import platform
import shutil
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from priority_living import __version__
from priority_living.config_manager import load_config


def handle_status(default_backend, default_anon_key):
    cfg = load_config()
    print("╔═══════════════════════════════════════════╗")
    print(f"║  Priority Living CLI  v{__version__:<18}║")
    print("╠═══════════════════════════════════════════╣")
    
    # System
    print(f"║  🖥  Machine:  {platform.node():<26}║")
    print(f"║  🐍 Python:   {sys.version.split()[0]:<26}║")
    print(f"║  💻 OS:       {platform.system()} {platform.release():<17}║")
    
    # Disk
    disk = shutil.disk_usage(str(Path.home()))
    free_gb = round(disk.free / (1024**3), 1)
    print(f"║  💾 Disk:     {free_gb} GB free{' ' * (20 - len(str(free_gb)))}║")
    
    # GPU
    gpu_status = _check_gpu()
    print(f"║  🎮 GPU:      {gpu_status:<26}║")
    
    # Dependencies
    deps = _check_deps()
    print(f"║  📦 Deps:     {deps:<26}║")
    
    # Bridge
    bridge_key = cfg.get("bridge_key", "")
    if bridge_key:
        bridge_status = _check_bridge(bridge_key, cfg.get("backend_url", default_backend), cfg.get("anon_key", default_anon_key))
        print(f"║  🔗 Bridge:   {bridge_status:<26}║")
    else:
        print(f"║  🔗 Bridge:   {'Not configured':<26}║")

    # Offline queue
    from priority_living.offline_queue import _load_queue
    queue = _load_queue()
    if queue:
        print(f"║  📦 Queue:    {len(queue)} pending{' ' * (19 - len(str(len(queue))))}║")
    
    # Models
    models = _list_local_models()
    print(f"║  🧠 Models:   {len(models)} installed{' ' * (17 - len(str(len(models))))}║")
    
    print("╚═══════════════════════════════════════════╝")


def handle_diagnose(default_backend, default_anon_key):
    cfg = load_config()
    print("🔍 Running deep diagnostic scan...\n")
    
    issues = []
    
    # 1. Python version
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 7):
        issues.append("❌ Python 3.7+ required")
    else:
        print(f"  ✅ Python {v.major}.{v.minor}.{v.micro}")
    
    # 2. GPU
    gpu = _check_gpu_detailed()
    if gpu["available"]:
        print(f"  ✅ GPU: {gpu['name']}")
    else:
        print(f"  ⚠️  No GPU detected (CPU-only inference)")
    
    # 3. Dependencies
    for pkg in ["requests", "torch", "transformers", "huggingface_hub"]:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg} installed")
        except ImportError:
            print(f"  ⚠️  {pkg} not installed")
    
    # 4. Bridge key
    bridge_key = cfg.get("bridge_key", "")
    if not bridge_key:
        issues.append("❌ No bridge key configured. Run: pl config set bridge_key pb_xxx")
        print("  ❌ Bridge key: not set")
    elif not bridge_key.startswith("pb_"):
        issues.append("❌ Invalid bridge key format")
        print("  ❌ Bridge key: invalid format")
    else:
        print("  ✅ Bridge key: configured")
    
    # 5. Network connectivity
    backend = cfg.get("backend_url", default_backend)
    try:
        start = time.time()
        req = urllib.request.Request(f"{backend}/functions/v1/bridge-poll", method="OPTIONS")
        req.add_header("Origin", "https://test.local")
        with urllib.request.urlopen(req, timeout=10) as resp:
            latency = round((time.time() - start) * 1000)
            print(f"  ✅ Backend reachable ({latency}ms latency)")
    except Exception as e:
        issues.append(f"❌ Cannot reach backend: {e}")
        print(f"  ❌ Backend unreachable: {e}")
    
    # 6. Models directory
    models_dir = Path.home() / ".priority-living" / "models"
    if models_dir.exists():
        models = [d.name for d in models_dir.iterdir() if d.is_dir()]
        print(f"  ✅ Models directory: {len(models)} models")
    else:
        print("  ℹ️  Models directory not created yet")

    # 7. Offline queue
    from priority_living.offline_queue import _load_queue
    queue = _load_queue()
    if queue:
        print(f"  ⚠️  Offline queue: {len(queue)} pending requests")
    else:
        print("  ✅ Offline queue: empty")

    # 8. Running agents
    agents_dir = Path.home() / ".priority-living" / "agents"
    if agents_dir.exists():
        pid_files = list(agents_dir.glob("*.pid"))
        running_count = 0
        for pf in pid_files:
            try:
                pid = int(pf.read_text().strip())
                os.kill(pid, 0)
                running_count += 1
            except Exception:
                pass
        print(f"  🤖 Agents: {running_count} running locally")
    else:
        print("  🤖 Agents: none running")
    
    # Summary
    print()
    if issues:
        print(f"⚠️  {len(issues)} issue(s) found:")
        for i in issues:
            print(f"   {i}")
    else:
        print("✅ All checks passed! System is ready.")


def _check_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)[:26]
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "Apple Silicon (MPS)"
        return "CPU only"
    except ImportError:
        return "torch not installed"


def _check_gpu_detailed():
    try:
        import torch
        if torch.cuda.is_available():
            return {"available": True, "name": torch.cuda.get_device_name(0), "type": "cuda"}
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return {"available": True, "name": "Apple Silicon (MPS)", "type": "mps"}
        return {"available": False, "name": "CPU only", "type": "cpu"}
    except ImportError:
        return {"available": False, "name": "torch not installed", "type": "none"}


def _check_deps():
    installed = []
    for pkg in ["torch", "transformers", "huggingface_hub"]:
        try:
            __import__(pkg)
            installed.append(pkg.split("_")[0][:4])
        except ImportError:
            pass
    return f"{len(installed)}/3 AI pkgs" if installed else "None installed"


def _check_bridge(key, backend, anon_key):
    try:
        url = f"{backend}/functions/v1/bridge-poll"
        headers = {
            "Content-Type": "application/json",
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "x-bridge-key": key,
        }
        data = json.dumps({"machine_name": "diag-check"}).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10):
            return "Connected ✅"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "Invalid key ❌"
        return f"Error ({e.code})"
    except Exception:
        return "Unreachable"


def _list_local_models():
    models_dir = Path.home() / ".priority-living" / "models"
    if not models_dir.exists():
        return []
    return [d.name for d in models_dir.iterdir() if d.is_dir()]
