"""Pure feature extraction; missing observations remain missing."""
from datetime import timedelta

from .contracts import instant


def dose_key(planned):
    # Exact dose matching is intentionally conservative for the first baseline.
    # Structural numeric equality treats JSON 60 and 60.0 as the same dose.
    return {"workout_type": planned["workout_type"],
            "stimuli": sorted(planned["stimuli"]), "dose": planned["dose"]}


def derive(record, sessions):
    actual, response = record["actual"], record["response"]
    ratio = actual["duration_min"] / record["planned"]["dose"]["duration_min"] if actual else None
    complete = bool(actual and response and actual["rpe"] is not None and actual["quality"] is not None
                    and all(response[k] is not None for k in ("pain", "recovery_24h", "recovery_48h", "next_session_quality")))
    adverse = bool((actual and (actual["execution"] == "C" or (ratio is not None and ratio < 0.8)
                     or (actual["quality"] is not None and actual["quality"] < 0.6)))
                   or (response and ((response["pain"] is not None and response["pain"] > 0)
                       or response["recovery_24h"] == "POOR" or response["recovery_48h"] == "POOR"
                       or response["next_session_quality"] == "POOR")))
    success = bool(complete and not adverse and actual["execution"] == "A" and 0.95 <= ratio <= 1.1
                   and actual["quality"] >= 0.8 and actual["rpe"] <= 8)
    previous, combination = None, None
    if actual:
        start = instant(actual["started_at"])
        candidates = []
        for other in sessions:
            prior = other["actual"]
            if prior is None or other is record:
                continue
            end = instant(prior["started_at"]) + timedelta(minutes=prior["duration_min"])
            gap = (start - end).total_seconds() / 3600
            if 0 <= gap <= 36:
                candidates.append((end, other["planned"]["session_id"], other, gap))
        if candidates:
            _, previous, prior, gap = max(candidates, key=lambda c: (c[0], c[1]))
            combination = f'{prior["planned"]["workout_type"]}->{record["planned"]["workout_type"]}:{"0-24h" if gap <= 24 else "24-36h"}'
    return {"session_id": record["planned"]["session_id"], "completion_ratio": ratio,
            "complete_response": complete, "success": success, "adverse": adverse,
            "previous_session_id": previous, "combination": combination}
