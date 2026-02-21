"""Priority Living CLI — Structured error reporting to cloud."""

import json
import platform
import sys
import traceback
import urllib.request
import urllib.error

from priority_living import __version__


def report_error(error, api_key="", backend="", anon_key=""):
    """Report a structured error to the cloud backend."""
    if not api_key or not backend:
        return

    try:
        error_data = {
            "command_id": None,
            "exit_code": -1,
            "output": json.dumps({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
                "cli_version": __version__,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "os": f"{platform.system()} {platform.release()}",
                "machine": platform.node(),
            }),
            "machine_name": platform.node(),
        }

        url = f"{backend}/functions/v1/bridge-result"
        headers = {
            "Content-Type": "application/json",
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "x-bridge-key": api_key,
        }
        body = json.dumps(error_data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass  # error reporting should never crash the CLI
