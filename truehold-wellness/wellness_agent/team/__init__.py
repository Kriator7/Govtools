"""TrueHold Wellness floor team: 20 hosts, rotation, and per-account favorite.

Tour state lives in gitignored data/team_hosts.json so /start sessions do not
wipe who the customer has already met. Same core replies; each host adds icon,
color, effect, and a few flavor lines from roster.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from wellness_agent.envfile import PACKAGE_ROOT

ROSTER_PATH = Path(__file__).resolve().parent / "roster.json"

_ROSTER: dict[str, Any] | None = None


def load_roster() -> dict[str, Any]:
    global _ROSTER
    if _ROSTER is None:
        _ROSTER = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    return _ROSTER


def members() -> list[dict[str, Any]]:
    return list(load_roster().get("members") or [])


def member_ids() -> list[str]:
    return [str(row["id"]) for row in members()]


def get_member(member_id: str | None) -> dict[str, Any]:
    wanted = str(member_id or "").strip().lower()
    for row in members():
        if str(row["id"]) == wanted:
            return row
    return members()[0]


def effect_id(member: dict[str, Any]) -> str:
    effects = load_roster().get("effects") or {}
    return str(effects.get(member.get("effect") or "party") or "")


def pose_line(member: dict[str, Any], pose: str) -> str:
    if pose == "wave":
        return str(member.get("hello") or "")
    return str(member.get(pose) or member.get("hello") or "")


def flavor_caption(
    member: dict[str, Any],
    pose: str,
    extra: str = "",
    *,
    joke: bool = False,
) -> str:
    heading = f"<b>{member['icon']} {member['name']}</b> · {member['role']}"
    body = f"{heading}\n{pose_line(member, pose)}"
    if joke and member.get("joke"):
        body = f"{body}\n\n<i>{member['joke']}</i>"
    if extra:
        body = f"{body}\n\n{extra}"
    return body


def hosts_path() -> Path:
    override = os.environ.get("WELLNESS_TEAM_HOSTS_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "team_hosts.json"


def _load() -> dict[str, Any]:
    path = hosts_path()
    if not path.is_file():
        return {"chats": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"chats": {}}
    chats = payload.get("chats") if isinstance(payload, dict) else None
    if not isinstance(chats, dict):
        return {"chats": {}}
    return {"chats": chats}


def _save(payload: dict[str, Any]) -> None:
    path = hosts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _entry(state: dict[str, Any], chat_id: str) -> dict[str, Any]:
    chats = state.setdefault("chats", {})
    entry = chats.get(chat_id)
    if not isinstance(entry, dict):
        entry = {"current": None, "favorite": None, "met": []}
        chats[chat_id] = entry
    entry.setdefault("current", None)
    entry.setdefault("favorite", None)
    if not isinstance(entry.get("met"), list):
        entry["met"] = []
    return entry


def host_record(chat_id: str) -> dict[str, Any]:
    state = _load()
    return dict(_entry(state, str(chat_id)))


def current_host(chat_id: str) -> dict[str, Any]:
    entry = host_record(chat_id)
    favorite = entry.get("favorite")
    if favorite:
        return get_member(str(favorite))
    current = entry.get("current")
    if current:
        return get_member(str(current))
    return members()[0]


def tour_complete(chat_id: str) -> bool:
    met = {str(item) for item in host_record(chat_id).get("met") or []}
    return len(met) >= len(members())


def favorite_id(chat_id: str) -> str | None:
    value = host_record(chat_id).get("favorite")
    return str(value) if value else None


def _next_unmet(entry: dict[str, Any]) -> dict[str, Any] | None:
    ids = member_ids()
    met = {str(item) for item in entry.get("met") or []}
    current = str(entry.get("current") or "")
    start = ids.index(current) + 1 if current in ids else 0
    for offset in range(len(ids)):
        candidate = ids[(start + offset) % len(ids)]
        if candidate not in met:
            return get_member(candidate)
    return None


def _cycle_next(entry: dict[str, Any]) -> dict[str, Any]:
    ids = member_ids()
    current = str(entry.get("current") or "")
    if current not in ids:
        return members()[0]
    return get_member(ids[(ids.index(current) + 1) % len(ids)])


def _assign(state: dict[str, Any], chat_id: str, member: dict[str, Any]) -> dict[str, Any]:
    entry = _entry(state, chat_id)
    entry["current"] = member["id"]
    met = entry.setdefault("met", [])
    if member["id"] not in met:
        met.append(member["id"])
    _save(state)
    return member


def advance_on_greet(chat_id: str) -> dict[str, Any]:
    """New host on each hello until the tour is done, unless a favorite is locked."""
    chat_id = str(chat_id)
    state = _load()
    entry = _entry(state, chat_id)
    locked = entry.get("favorite")
    if locked:
        return _assign(state, chat_id, get_member(str(locked)))
    unmet = _next_unmet(entry)
    if unmet is None:
        current = entry.get("current")
        member = get_member(str(current)) if current else members()[0]
        _save(state)
        return member
    return _assign(state, chat_id, unmet)


def skip_to_next(chat_id: str) -> dict[str, Any]:
    """Meet-the-next-teammate button. Favorite stays locked if set."""
    chat_id = str(chat_id)
    state = _load()
    entry = _entry(state, chat_id)
    locked = entry.get("favorite")
    if locked:
        return _assign(state, chat_id, get_member(str(locked)))
    unmet = _next_unmet(entry)
    member = unmet if unmet is not None else _cycle_next(entry)
    return _assign(state, chat_id, member)


def set_favorite(chat_id: str, member_id: str) -> dict[str, Any]:
    chat_id = str(chat_id)
    member = get_member(member_id)
    state = _load()
    entry = _entry(state, chat_id)
    entry["favorite"] = member["id"]
    return _assign(state, chat_id, member)


def clear_favorite(chat_id: str) -> dict[str, Any]:
    chat_id = str(chat_id)
    state = _load()
    entry = _entry(state, chat_id)
    entry["favorite"] = None
    _save(state)
    return current_host(chat_id)


def rotate_again(chat_id: str) -> dict[str, Any]:
    """Wipe the tour and start with the first host. Clears favorite."""
    chat_id = str(chat_id)
    state = _load()
    _entry(state, chat_id)
    state["chats"][chat_id] = {"current": None, "favorite": None, "met": []}
    _save(state)
    return advance_on_greet(chat_id)
