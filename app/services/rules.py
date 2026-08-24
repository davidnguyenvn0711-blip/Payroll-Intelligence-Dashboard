from __future__ import annotations

import json
from datetime import date
from pathlib import Path


RULES_PATH = Path(__file__).parents[2] / "config" / "payroll_rules.json"


def load_config(path: Path = RULES_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def effective_rules(on_date: date, config: dict | None = None) -> dict[str, dict]:
    config = config or load_config()
    result = {}
    for rule in config["rules"]:
        start = date.fromisoformat(rule["effective_from"])
        end = date.fromisoformat(rule["effective_to"]) if rule["effective_to"] else None
        if start <= on_date and (end is None or on_date <= end):
            result[rule["name"]] = rule
    return result


def unverified_rules(config: dict | None = None) -> list[str]:
    config = config or load_config()
    statuses = {r["name"]: r["status"] for r in config["rules"]}
    return [name for name in config["unverified_required"] if statuses.get(name) != "Đã xác minh"]

