import json
import os
from datetime import date

DEFAULT_STATE = {
    "date": str(date.today()),
    "posts_today": 0,
    "replied_ids": [],
    "dm_replied_ids": [],
}

def load_state(path="state.json") -> dict:
    if not os.path.exists(path):
        return DEFAULT_STATE.copy()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict, path="state.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def increment_post_count(state: dict) -> dict:
    state["posts_today"] = state.get("posts_today", 0) + 1
    return state

def mark_replied(state: dict, post_id: str) -> dict:
    if post_id not in state["replied_ids"]:
        state["replied_ids"].append(post_id)
    return state

def mark_dm_replied(state: dict, dm_id: str) -> dict:
    if dm_id not in state["dm_replied_ids"]:
        state["dm_replied_ids"].append(dm_id)
    return state

def reset_daily(state: dict) -> dict:
    state["date"] = str(date.today())
    state["posts_today"] = 0
    state["replied_ids"] = []
    return state
