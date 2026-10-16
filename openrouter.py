#!/usr/bin/env python3
"""OpenRouter credits as an `omp usage --json` style report, for Panel.qml.

The API key is the one logged in to Oh My Pi (agent.db, provider "openrouter"),
read-only. Prints nothing when OpenRouter is not logged in or unreachable, so
the panel just shows no OpenRouter row.
"""
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

DB = Path.home() / ".omp/agent/agent.db"
API = "https://openrouter.ai/api/v1/"


def api_key():
    try:
        db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
        row = db.execute(
            "select data from auth_credentials where provider = 'openrouter' "
            "and disabled_cause is null order by updated_at desc limit 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    return json.loads(row[0]).get("key") if row else None


def get(path, key):
    request = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)["data"]


def report(credits, key_info, now):
    total, used = float(credits["total_credits"]), float(credits["total_usage"])
    fraction = min(1.0, used / total) if total > 0 else 1.0
    limits = [{
        "id": "openrouter:credits",
        "label": "Credits",
        "scope": {"provider": "openrouter", "windowId": "credits", "shared": True},
        "window": {"id": "credits", "label": "Credits"},
        "amount": {
            "used": used, "limit": total, "remaining": max(0.0, total - used),
            "usedFraction": fraction, "remainingFraction": 1 - fraction, "unit": "usd",
        },
        "status": "exhausted" if fraction >= 1 else "ok",
    }]
    if key_info.get("usage_daily") is not None:
        limits.append({
            "id": "openrouter:today",
            "label": "Today",
            "scope": {"provider": "openrouter", "windowId": "1d", "shared": True},
            "window": {"id": "1d", "label": "Today"},
            "amount": {"used": float(key_info["usage_daily"]), "unit": "usd"},
            "status": "ok",
        })
    return {
        "provider": "openrouter",
        "fetchedAt": now,
        "limits": limits,
        "metadata": {"planType": "credits"},
    }


def main():
    key = api_key()
    if not key:
        return
    try:
        credits, key_info = get("credits", key), get("key", key)
    except (OSError, ValueError, KeyError):
        return
    print(json.dumps({"reports": [report(credits, key_info, int(time.time() * 1000))]}))


if __name__ == "__main__":
    main()
