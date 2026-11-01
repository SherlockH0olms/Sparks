"""Readable registry and test names; evidence identifiers and snapshots stay fixed."""
from collections import Counter


def name_key(name: str) -> str:
    return " ".join(name.split()).casefold()


def target_names(store, workspace: str) -> dict[str, dict]:
    history = store.registration_history("target", workspace)
    totals = Counter(name_key(row["name"]) for row in history)
    positions = Counter()
    latest_models = {row["model"].casefold(): row["id"] for row in history}
    result = {}
    for row in history:
        key = name_key(row["name"])
        positions[key] += 1
        number = positions[key]
        base = " ".join(row["name"].split())
        result[row["id"]] = {"display_name": f"{base} {number}" if totals[key] > 1 else base,
            "registration_number": number, "created_at": row["created_at"],
            "is_latest_for_model": latest_models[row["model"].casefold()] == row["id"],
            "model": row["model"]}
    # A literal name such as "Assistant 1" must not collide with a generated one.
    duplicates = Counter(name_key(item["display_name"]) for item in result.values())
    for registration, row in enumerate(history, 1):
        item = result[row["id"]]
        if duplicates[name_key(item["display_name"])] > 1:
            item["display_name"] += f" (registration {registration})"
    return result


def campaign_names(store, workspace: str) -> dict[str, dict]:
    history = store.registration_history("campaign", workspace)
    return {row["id"]: {"display_name": f"Test {number}", "run_number": number,
            "is_latest": number == len(history), "created_at": row["created_at"]}
            for number, row in enumerate(history, 1)}


def campaign_name(campaign: dict, names: dict, targets: dict) -> dict:
    target = targets.get(campaign["target_id"], {})
    return names[campaign["id"]] | {"target_name": target.get("display_name", "Registered target"),
                                    "target_model": target.get("model", "")}
