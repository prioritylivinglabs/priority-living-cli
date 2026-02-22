#!/usr/bin/env python3
"""
Priority Living CLI — Main entry point.
Usage: pl <command> [options]
"""

import argparse
import sys

from priority_living import __version__

def main():
    parser = argparse.ArgumentParser(
        prog="pl",
        description="Priority Living CLI — Sovereign AI command & control",
    )
    parser.add_argument("--version", action="version", version=f"Priority Living CLI v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── bridge ──────────────────────────────────────────
    bridge_parser = subparsers.add_parser("bridge", help="Bridge worker management")
    bridge_sub = bridge_parser.add_subparsers(dest="bridge_action")
    start_parser = bridge_sub.add_parser("start", help="Start the bridge worker")
    start_parser.add_argument("--key", "-k", help="Bridge API key (pb_...)")
    start_parser.add_argument("--name", "-n", help="Machine name")
    start_parser.add_argument("--poll-interval", type=int, default=3, help="Poll interval (seconds)")
    start_parser.add_argument("--auto-restart", action="store_true", help="Auto-restart on crash")

    # ── agents ──────────────────────────────────────────
    agents_parser = subparsers.add_parser("agents", help="Agent management")
    agents_sub = agents_parser.add_subparsers(dest="agents_action")
    agents_sub.add_parser("list", help="List agents bound to this bridge")
    agent_start = agents_sub.add_parser("start", help="Start a local agent worker")
    agent_start.add_argument("agent_id", help="Agent ID to start")
    agent_start.add_argument("--poll-interval", type=int, default=5, help="Task poll interval (seconds)")
    agent_stop = agents_sub.add_parser("stop", help="Stop a running agent worker")
    agent_stop.add_argument("agent_id", help="Agent ID to stop")
    agent_deploy = agents_sub.add_parser("deploy", help="Deploy an agent")
    agent_deploy.add_argument("platform", help="Platform (e.g. telegram)")
    agent_deploy.add_argument("--agent-id", required=True, help="Agent ID")

    # ── models ──────────────────────────────────────────
    models_parser = subparsers.add_parser("models", help="Local model management")
    models_sub = models_parser.add_subparsers(dest="models_action")
    dl_parser = models_sub.add_parser("download", help="Download a HuggingFace model")
    dl_parser.add_argument("model_name", help="Model name (e.g. microsoft/phi-2)")
    infer_parser = models_sub.add_parser("infer", help="Run local inference")
    infer_parser.add_argument("model_name", help="Model name")
    infer_parser.add_argument("--prompt", "-p", required=True, help="Prompt text")
    infer_parser.add_argument("--max-tokens", type=int, default=256, help="Max tokens")
    serve_parser = models_sub.add_parser("serve", help="Start local model API server")
    serve_parser.add_argument("model_name", help="Model name")
    serve_parser.add_argument("--port", type=int, default=8000, help="Server port")

    # ── status / diagnose ───────────────────────────────
    subparsers.add_parser("status", help="Show system & bridge status")
    subparsers.add_parser("diagnose", help="Deep diagnostic scan")

    # ── update ──────────────────────────────────────────
    subparsers.add_parser("update", help="Check for updates and self-update")

    # ── config ──────────────────────────────────────────
    config_parser = subparsers.add_parser("config", help="Local configuration")
    config_sub = config_parser.add_subparsers(dest="config_action")
    set_parser = config_sub.add_parser("set", help="Set a config value")
    set_parser.add_argument("key", help="Config key")
    set_parser.add_argument("value", help="Config value")
    get_parser = config_sub.add_parser("get", help="Get a config value")
    get_parser.add_argument("key", help="Config key")

    # ── gui ─────────────────────────────────────────────
    gui_parser = subparsers.add_parser("gui", help="Launch local WebGUI dashboard")
    gui_parser.add_argument("--port", type=int, default=8420, help="Server port (default: 8420)")
    gui_parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Route commands
    if args.command == "bridge":
        from priority_living.bridge import handle_bridge
        handle_bridge(args, "https://thwyuilswskxejzjwkyr.supabase.co", "sb_publishable_xDyzIQsSNLeAF7DfJ_zddQ_vMmI-SZj")
    elif args.command == "agents":
        from priority_living.agents import handle_agents
        handle_agents(args, "https://thwyuilswskxejzjwkyr.supabase.co", "sb_publishable_xDyzIQsSNLeAF7DfJ_zddQ_vMmI-SZj")
    elif args.command == "models":
        from priority_living.models import handle_models
        handle_models(args)
    elif args.command == "status":
        from priority_living.diagnostics import handle_status
        handle_status("https://thwyuilswskxejzjwkyr.supabase.co", "sb_publishable_xDyzIQsSNLeAF7DfJ_zddQ_vMmI-SZj")
    elif args.command == "diagnose":
        from priority_living.diagnostics import handle_diagnose
        handle_diagnose("https://thwyuilswskxejzjwkyr.supabase.co", "sb_publishable_xDyzIQsSNLeAF7DfJ_zddQ_vMmI-SZj")
    elif args.command == "update":
        from priority_living.updater import handle_update
        handle_update()
    elif args.command == "config":
        from priority_living.config_manager import handle_config
        handle_config(args)
    elif args.command == "gui":
        from priority_living.gui import handle_gui
        handle_gui(args, "https://thwyuilswskxejzjwkyr.supabase.co", "sb_publishable_xDyzIQsSNLeAF7DfJ_zddQ_vMmI-SZj")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
