"""Read/write Facebook settings in the project's .env file."""

import os
import re

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

KEYS = ("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN", "FB_API_VERSION", "DEMO_MODE")


def read_settings():
    """Current effective settings (env vars, which load_dotenv populated)."""
    return {
        "FB_PAGE_ID": os.getenv("FB_PAGE_ID", ""),
        "FB_PAGE_ACCESS_TOKEN": os.getenv("FB_PAGE_ACCESS_TOKEN", ""),
        "FB_API_VERSION": os.getenv("FB_API_VERSION", "v21.0"),
        "DEMO_MODE": os.getenv("DEMO_MODE", "false"),
    }


def save_settings(updates):
    """Persist the given keys to .env (creating it if needed) and apply them
    to the running process so the change takes effect immediately."""
    updates = {k: v for k, v in updates.items() if k in KEYS and v is not None}

    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    remaining = dict(updates)
    out = []
    for line in lines:
        m = re.match(r"^\s*([A-Z_]+)\s*=", line)
        if m and m.group(1) in remaining:
            out.append(f"{m.group(1)}={remaining.pop(m.group(1))}")
        else:
            out.append(line)
    for key, value in remaining.items():
        out.append(f"{key}={value}")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip("\n") + "\n")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass

    for key, value in updates.items():
        os.environ[key] = value
