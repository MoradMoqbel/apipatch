"""
ApiPatch Anonymous Telemetry Module
Privacy-preserving, non-blocking telemetry to measure real CLI usage and adoption.
No sensitive data, source code, file contents, tokens, or repo names are ever sent.
Supports standard opt-out (DO_NOT_TRACK=1, APIPATCH_NO_TELEMETRY=1).
"""

import os
import sys
import json
import uuid
import platform
import threading
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

# PostHog public ingestion endpoint
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")
# PostHog Project API Key (can be set via env or hardcoded project key)
DEFAULT_POSTHOG_KEY = os.getenv("APIPATCH_POSTHOG_KEY", "phc_BBVP3bov5fsF8W24hLHZjcd9GKT9xPEy8idRJfnHWC5h")

_ANON_ID_CACHE = None


def is_telemetry_enabled() -> bool:
    """Checks if telemetry is allowed by user environment variables."""
    opt_out_envs = [
        "DO_NOT_TRACK",
        "APIPATCH_NO_TELEMETRY",
        "APIPATCH_DISABLE_TELEMETRY",
        "APIPATCH_TELEMETRY_DISABLED"
    ]
    for var in opt_out_envs:
        val = os.getenv(var, "").strip().lower()
        if val in ("1", "true", "yes", "on"):
            return False
    return True


def get_anonymous_id() -> str:
    """Returns a persistent anonymous UUID for the machine."""
    global _ANON_ID_CACHE
    if _ANON_ID_CACHE:
        return _ANON_ID_CACHE

    config_dir = os.path.expanduser("~/.apipatch")
    id_file = os.path.join(config_dir, "telemetry_id")

    try:
        if os.path.exists(id_file):
            with open(id_file, "r", encoding="utf-8") as f:
                anon_id = f.read().strip()
                if anon_id:
                    _ANON_ID_CACHE = anon_id
                    return anon_id
    except Exception:
        pass

    # Generate new random anonymous UUID
    anon_id = str(uuid.uuid4())
    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(id_file, "w", encoding="utf-8") as f:
            f.write(anon_id)
    except Exception:
        pass

    _ANON_ID_CACHE = anon_id
    return anon_id


def _send_payload_async(payload: dict) -> None:
    """Internal function that sends JSON payload to ingestion API with strict timeout."""
    try:
        data = json.dumps(payload).encode("utf-8")
        url = f"{POSTHOG_HOST}/capture/"
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ApiPatch-Telemetry/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=1.5):
            pass
    except Exception:
        # Guaranteed failure silence: never interrupt developer workflows
        pass


def track_cli_event(
    command: str,
    properties: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> None:
    """
    Asynchronously tracks an anonymous CLI command event in a non-blocking daemon thread.
    Never sends code, secrets, repository names, or paths.
    """
    if not is_telemetry_enabled():
        return

    posthog_key = api_key or DEFAULT_POSTHOG_KEY
    if not posthog_key:
        return

    try:
        from apipatch._version import __version__
        version = __version__
    except Exception:
        version = "unknown"

    event_properties = {
        "command": command,
        "apipatch_version": version,
        "os": platform.system(),
        "os_release": platform.release(),
        "python_version": platform.python_version(),
    }

    if properties:
        # Only allow safe primitive values
        for k, v in properties.items():
            if isinstance(v, (str, int, float, bool)):
                event_properties[k] = v

    payload = {
        "api_key": posthog_key,
        "event": "cli_command",
        "distinct_id": get_anonymous_id(),
        "properties": event_properties
    }

    # Dispatch in a daemon thread so it never blocks CLI exit or slows down user
    thread = threading.Thread(target=_send_payload_async, args=(payload,), daemon=True)
    thread.start()
