"""Priority Living CLI — Offline command queue for resilient API calls."""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

QUEUE_DIR = Path.home() / ".priority-living"
QUEUE_FILE = QUEUE_DIR / "offline_queue.json"
MAX_QUEUE_SIZE = 500


def _load_queue():
    """Load the offline queue from disk."""
    if not QUEUE_FILE.exists():
        return []
    try:
        with open(QUEUE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_queue(queue):
    """Save the offline queue to disk."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def enqueue(endpoint, data, method="POST"):
    """Add a failed request to the offline queue."""
    queue = _load_queue()
    entry = {
        "endpoint": endpoint,
        "data": data,
        "method": method,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    queue.append(entry)
    # Enforce max size — drop oldest if exceeded
    if len(queue) > MAX_QUEUE_SIZE:
        dropped = len(queue) - MAX_QUEUE_SIZE
        queue = queue[dropped:]
        print(f"  ⚠ Offline queue full, dropped {dropped} oldest entries")
    _save_queue(queue)
    print(f"  📦 Queued offline: {endpoint} ({len(queue)} pending)")


def try_drain_queue(api_key="", backend="", anon_key=""):
    """Attempt to replay queued requests. Called at top of each poll cycle."""
    queue = _load_queue()
    if not queue:
        return

    remaining = []
    drained = 0

    for entry in queue:
        try:
            url = f"{backend}/functions/v1/{entry['endpoint']}"
            headers = {
                "Content-Type": "application/json",
                "apikey": anon_key,
                "Authorization": f"Bearer {anon_key}",
                "x-bridge-key": api_key,
            }
            body = json.dumps(entry["data"]).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers, method=entry.get("method", "POST"))
            with urllib.request.urlopen(req, timeout=15):
                drained += 1
        except (urllib.error.URLError, OSError):
            # Still offline — stop draining, keep the rest
            remaining.append(entry)
            remaining.extend(queue[queue.index(entry) + 1:])
            break
        except urllib.error.HTTPError as e:
            if e.code >= 500:
                # Server error — keep for retry
                remaining.append(entry)
            else:
                # Client error (4xx) — discard, it won't succeed on retry
                drained += 1
        except Exception:
            remaining.append(entry)

    if drained > 0:
        print(f"  📤 Drained {drained} queued request(s)")
    _save_queue(remaining)


def resilient_request(endpoint, data=None, method="POST", api_key="", backend="", anon_key=""):
    """Make an API request with offline queue fallback.

    On network failure, the request is queued locally for later replay.
    Returns the response dict on success, or None on failure (after queueing).
    """
    url = f"{backend}/functions/v1/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "x-bridge-key": api_key,
    }
    try:
        if data:
            body = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError):
        # Network unreachable — queue for later
        if data:
            enqueue(endpoint, data, method)
        return None
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  ⚠ API error {e.code}: {body_text[:200]}")
        if e.code >= 500 and data:
            enqueue(endpoint, data, method)
        return None
    except Exception as e:
        print(f"  ⚠ Request failed: {e}")
        if data:
            enqueue(endpoint, data, method)
        return None
