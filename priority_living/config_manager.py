"""Priority Living CLI — Local configuration manager."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".priority-living"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "bridge_key": "",
    "backend_url": "",
    "anon_key": "",
    "default_model_path": str(CONFIG_DIR / "models"),
    "poll_interval": 3,
    "auto_restart": True,
    "machine_name": "",
    "github_repo_owner": "",
    "connection_token": "",
}


def load_config():
    """Load config from ~/.priority-living/config.json"""
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    """Save config to ~/.priority-living/config.json"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def handle_config(args):
    if not args.config_action:
        # Show all config
        cfg = load_config()
        print("⚙️  Current configuration:")
        for k, v in cfg.items():
            display_v = v
            if k in ("bridge_key", "connection_token") and v:
                display_v = v[:6] + "..." + v[-4:] if len(v) > 10 else "***"
            print(f"   {k}: {display_v}")
        print(f"\n   Config file: {CONFIG_FILE}")
        return

    if args.config_action == "set":
        cfg = load_config()
        # Type conversion for known keys
        if args.key in ("poll_interval",):
            cfg[args.key] = int(args.value)
        elif args.key in ("auto_restart",):
            cfg[args.key] = args.value.lower() in ("true", "1", "yes")
        else:
            cfg[args.key] = args.value
        save_config(cfg)
        display = args.value
        if args.key in ("bridge_key", "connection_token"):
            display = args.value[:6] + "..." if len(args.value) > 6 else "***"
        print(f"✅ Set {args.key} = {display}")

    elif args.config_action == "get":
        cfg = load_config()
        val = cfg.get(args.key, "[not set]")
        if args.key in ("bridge_key", "connection_token") and val:
            val = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
        print(f"{args.key}: {val}")
