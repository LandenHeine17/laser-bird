"""Persist progress (records, tokens, upgrades, unlocks) to save.json."""
import copy
import json
import os

# Set to None to disable saving entirely (the test scripts do this).
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "save.json")

DEFAULTS = {
    "high": 0, "best_tier": 0, "runs": 0,          # endless records + run count
    "shards": 0, "tokens": 0, "skin": 0,           # lifetime shards unlock skins; tokens are spent in the shop
    "unlocked": 1, "secret": False,                # adventure progress
    "upgrades": {}, "lasers": ["standard"], "laser": "standard",
    "best": [], "stars": [],                       # per-level records, indexed like worlds.LEVELS
}


def load(num_levels):
    data = copy.deepcopy(DEFAULTS)
    if PATH:
        try:
            with open(PATH) as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                data.update(stored)
        except (OSError, ValueError):
            pass
    for key in ("best", "stars"):
        v = data[key] if isinstance(data[key], list) else []
        data[key] = v + [0] * (num_levels - len(v))
    return data


def save(data):
    if not PATH:
        return
    tmp = PATH + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, PATH)  # atomic: a crash mid-write can't corrupt the save
    except OSError as e:
        print("Could not save:", e)
