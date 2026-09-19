from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import machine_root


PROFILE_ID = "doll/odd-shift-duo@1"


def profile_directory(profile_id: str = PROFILE_ID) -> Path:
    if profile_id != PROFILE_ID:
        raise ValueError(f"unsupported profile {profile_id!r}; only {PROFILE_ID!r} is implemented")
    return machine_root() / "profiles" / "doll" / "odd-shift-duo"


def load_profile(profile_id: str = PROFILE_ID) -> dict[str, Any]:
    path = profile_directory(profile_id) / "profile.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("id") != PROFILE_ID:
        raise ValueError("profile identity mismatch")
    return profile

