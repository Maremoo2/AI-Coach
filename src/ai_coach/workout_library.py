"""Small, versioned workout library used for HQ-approved variants and on-demand proposals."""

from copy import deepcopy

LIBRARY_VERSION = "1.0"

TEMPLATES = {
    "RUN_EASY_45": {
        "workout_type": "RUN_EASY", "sport": "RUN", "duration_min": 45,
        "quality": False, "venues": ["OUTDOOR", "EVO_TREADMILL"],
        "progression_family": "RUN_EASY",
        "steps": [
            {"name": "easy", "duration_min": 40, "target": "conversational / easy aerobic"},
            {"name": "strides_optional", "reps": 4, "duration_sec": 20, "target": "relaxed fast, full control"},
        ],
    },
    "RUN_EASY_60": {
        "workout_type": "RUN_EASY", "sport": "RUN", "duration_min": 60,
        "quality": False, "venues": ["OUTDOOR", "EVO_TREADMILL"],
        "progression_family": "RUN_EASY",
        "steps": [{"name": "easy", "duration_min": 60, "target": "conversational / easy aerobic"}],
    },
    "RUN_THRESHOLD_3X8": {
        "workout_type": "RUN_THRESHOLD", "sport": "RUN", "duration_min": 55,
        "quality": True, "venues": ["OUTDOOR", "EVO_TREADMILL"],
        "progression_family": "RUN_THRESHOLD",
        "steps": [
            {"name": "warmup", "duration_min": 15, "target": "easy"},
            {"name": "work", "reps": 3, "duration_min": 8, "recovery_min": 2, "target": "threshold"},
            {"name": "cooldown", "duration_min": 10, "target": "easy"},
        ],
    },
    "RUN_THRESHOLD_3X10": {
        "workout_type": "RUN_THRESHOLD", "sport": "RUN", "duration_min": 62,
        "quality": True, "venues": ["OUTDOOR", "EVO_TREADMILL"],
        "progression_family": "RUN_THRESHOLD",
        "steps": [
            {"name": "warmup", "duration_min": 15, "target": "easy"},
            {"name": "work", "reps": 3, "duration_min": 10, "recovery_min": 2, "target": "threshold"},
            {"name": "cooldown", "duration_min": 12, "target": "easy"},
        ],
    },
    "RUN_THRESHOLD_3X12": {
        "workout_type": "RUN_THRESHOLD", "sport": "RUN", "duration_min": 70,
        "quality": True, "venues": ["OUTDOOR", "EVO_TREADMILL"],
        "progression_family": "RUN_THRESHOLD",
        "steps": [
            {"name": "warmup", "duration_min": 15, "target": "easy"},
            {"name": "work", "reps": 3, "duration_min": 12, "recovery_min": 2, "target": "threshold"},
            {"name": "cooldown", "duration_min": 15, "target": "easy"},
        ],
    },
    "RUN_INTERVAL_5X4": {
        "workout_type": "RUN_INTERVAL", "sport": "RUN", "duration_min": 58,
        "quality": True, "venues": ["OUTDOOR", "EVO_TREADMILL"],
        "progression_family": "RUN_INTERVAL",
        "steps": [
            {"name": "warmup", "duration_min": 18, "target": "easy + drills"},
            {"name": "work", "reps": 5, "duration_min": 4, "recovery_min": 2, "target": "controlled VO2 / 5k-ish effort"},
            {"name": "cooldown", "duration_min": 10, "target": "easy"},
        ],
    },
    "RUN_LONG_90": {
        "workout_type": "RUN_LONG", "sport": "RUN", "duration_min": 90,
        "quality": False, "venues": ["OUTDOOR"], "progression_family": "RUN_LONG",
        "steps": [{"name": "endurance", "duration_min": 90, "target": "easy aerobic; durable form"}],
    },
    "RUN_LONG_120": {
        "workout_type": "RUN_LONG", "sport": "RUN", "duration_min": 120,
        "quality": False, "venues": ["OUTDOOR"], "progression_family": "RUN_LONG",
        "steps": [{"name": "endurance", "duration_min": 120, "target": "easy aerobic; fuel and hydrate"}],
    },
    "BIKE_AEROBIC_60": {
        "workout_type": "BIKE_AEROBIC", "sport": "BIKE", "duration_min": 60,
        "quality": False, "venues": ["MYWHOOSH", "OUTDOOR"], "progression_family": "BIKE_AEROBIC",
        "steps": [
            {"name": "warmup", "duration_min": 10, "ftp_pct": [0.50, 0.65]},
            {"name": "aerobic", "duration_min": 45, "ftp_pct": [0.60, 0.72]},
            {"name": "cooldown", "duration_min": 5, "ftp_pct": [0.45, 0.55]},
        ],
    },
    "BIKE_ENDURANCE_90": {
        "workout_type": "BIKE_ENDURANCE", "sport": "BIKE", "duration_min": 90,
        "quality": False, "venues": ["MYWHOOSH", "OUTDOOR"], "progression_family": "BIKE_AEROBIC",
        "steps": [
            {"name": "warmup", "duration_min": 10, "ftp_pct": [0.50, 0.65]},
            {"name": "endurance", "duration_min": 75, "ftp_pct": [0.62, 0.74]},
            {"name": "cooldown", "duration_min": 5, "ftp_pct": [0.45, 0.55]},
        ],
    },
    "BIKE_SWEETSPOT_2X15": {
        "workout_type": "BIKE_SWEETSPOT", "sport": "BIKE", "duration_min": 60,
        "quality": True, "venues": ["MYWHOOSH", "OUTDOOR"], "progression_family": "BIKE_SWEETSPOT",
        "steps": [
            {"name": "warmup", "duration_min": 12, "ftp_pct": [0.50, 0.72]},
            {"name": "work", "reps": 2, "duration_min": 15, "recovery_min": 5, "ftp_pct": [0.88, 0.92]},
            {"name": "cooldown", "duration_min": 8, "ftp_pct": [0.45, 0.60]},
        ],
    },
    "BIKE_SWEETSPOT_3X15": {
        "workout_type": "BIKE_SWEETSPOT", "sport": "BIKE", "duration_min": 78,
        "quality": True, "venues": ["MYWHOOSH", "OUTDOOR"], "progression_family": "BIKE_SWEETSPOT",
        "steps": [
            {"name": "warmup", "duration_min": 12, "ftp_pct": [0.50, 0.72]},
            {"name": "work", "reps": 3, "duration_min": 15, "recovery_min": 5, "ftp_pct": [0.88, 0.92]},
            {"name": "cooldown", "duration_min": 6, "ftp_pct": [0.45, 0.60]},
        ],
    },
    "BIKE_THRESHOLD_4X8": {
        "workout_type": "BIKE_THRESHOLD", "sport": "BIKE", "duration_min": 70,
        "quality": True, "venues": ["MYWHOOSH", "OUTDOOR"], "progression_family": "BIKE_THRESHOLD",
        "steps": [
            {"name": "warmup", "duration_min": 15, "ftp_pct": [0.50, 0.75]},
            {"name": "work", "reps": 4, "duration_min": 8, "recovery_min": 4, "ftp_pct": [0.95, 1.02]},
            {"name": "cooldown", "duration_min": 11, "ftp_pct": [0.45, 0.60]},
        ],
    },
    "BIKE_VO2_5X4": {
        "workout_type": "BIKE_VO2", "sport": "BIKE", "duration_min": 65,
        "quality": True, "venues": ["MYWHOOSH"], "progression_family": "BIKE_VO2",
        "steps": [
            {"name": "warmup", "duration_min": 15, "ftp_pct": [0.50, 0.75]},
            {"name": "work", "reps": 5, "duration_min": 4, "recovery_min": 4, "ftp_pct": [1.08, 1.18]},
            {"name": "cooldown", "duration_min": 10, "ftp_pct": [0.45, 0.60]},
        ],
    },
    "SWIM_TECHNIQUE_1800": {
        "workout_type": "SWIM_TECHNIQUE", "sport": "SWIM", "duration_min": 50,
        "quality": False, "venues": ["POOL"], "progression_family": "SWIM_TECHNIQUE",
        "steps": [
            {"name": "easy", "distance_m": 300},
            {"name": "drills", "distance_m": 600, "target": "technique quality"},
            {"name": "aerobic", "distance_m": 700, "target": "smooth"},
            {"name": "easy", "distance_m": 200},
        ],
    },
    "SWIM_CSS_10X100": {
        "workout_type": "SWIM_CSS", "sport": "SWIM", "duration_min": 55,
        "quality": True, "venues": ["POOL"], "progression_family": "SWIM_CSS",
        "steps": [
            {"name": "warmup", "distance_m": 500},
            {"name": "work", "reps": 10, "distance_m": 100, "recovery_sec": 20, "target": "CSS"},
            {"name": "easy", "distance_m": 300},
        ],
    },
    "STRENGTH_EVO_FULLBODY_A": {
        "workout_type": "STRENGTH_FULLBODY", "sport": "STRENGTH", "duration_min": 55,
        "quality": True, "venues": ["EVO_GYM"], "progression_family": "STRENGTH_FULLBODY",
        "steps": [
            {"exercise": "squat_pattern", "sets": 3, "reps": "6-8", "rir": "2-3"},
            {"exercise": "bench_press", "sets": 3, "reps": "6-8", "rir": "2-3"},
            {"exercise": "row", "sets": 3, "reps": "8-12", "rir": "2-3"},
            {"exercise": "hinge_or_leg_curl", "sets": 2, "reps": "8-12", "rir": "2-3"},
            {"exercise": "lat_pulldown", "sets": 2, "reps": "8-12", "rir": "2-3"},
            {"exercise": "anti_extension_core", "sets": 2, "reps": "controlled", "rir": "2-3"},
        ],
    },
    "STRENGTH_EVO_MINIMUM": {
        "workout_type": "STRENGTH_FULLBODY", "sport": "STRENGTH", "duration_min": 30,
        "quality": False, "venues": ["EVO_GYM"], "progression_family": "STRENGTH_FULLBODY",
        "steps": [
            {"exercise": "squat_pattern", "sets": 2, "reps": "8-10", "rir": "3"},
            {"exercise": "press", "sets": 2, "reps": "8-10", "rir": "3"},
            {"exercise": "row_or_pulldown", "sets": 2, "reps": "10-12", "rir": "3"},
            {"exercise": "core", "sets": 2, "reps": "controlled", "rir": "3"},
        ],
    },
    "RECOVERY_30": {
        "workout_type": "RECOVERY", "sport": "MIXED", "duration_min": 30,
        "quality": False, "venues": ["OUTDOOR", "EVO_GYM", "HOME"], "progression_family": "RECOVERY",
        "steps": [{"name": "easy_movement", "duration_min": 30, "target": "very easy / restorative"}],
    },
}

PROGRESSION_FAMILIES = {
    "RUN_EASY": ["RUN_EASY_45", "RUN_EASY_60"],
    "RUN_THRESHOLD": ["RUN_THRESHOLD_3X8", "RUN_THRESHOLD_3X10", "RUN_THRESHOLD_3X12"],
    "RUN_LONG": ["RUN_LONG_90", "RUN_LONG_120"],
    "BIKE_AEROBIC": ["BIKE_AEROBIC_60", "BIKE_ENDURANCE_90"],
    "BIKE_SWEETSPOT": ["BIKE_SWEETSPOT_2X15", "BIKE_SWEETSPOT_3X15"],
    "STRENGTH_FULLBODY": ["STRENGTH_EVO_MINIMUM", "STRENGTH_EVO_FULLBODY_A"],
}


def template(template_id):
    if template_id not in TEMPLATES:
        raise ValueError(f"Unknown workout template: {template_id}")
    result = deepcopy(TEMPLATES[template_id])
    result["template_id"] = template_id
    result["library_version"] = LIBRARY_VERSION
    return result


def step_template(template_id, direction):
    current = template(template_id)
    family = PROGRESSION_FAMILIES.get(current["progression_family"], [template_id])
    if template_id not in family:
        return template_id
    index = family.index(template_id)
    if direction == "UP":
        return family[min(index + 1, len(family) - 1)]
    if direction == "DOWN":
        return family[max(index - 1, 0)]
    return template_id


def _watts(ftp, pct):
    return int(round(float(ftp) * pct))


def prescribe(template_id, capacities=None, venue=None):
    capacities = capacities or {}
    result = template(template_id)
    if venue is not None:
        if venue not in result["venues"]:
            raise ValueError(f"{venue} is not supported for {template_id}")
        result["venue"] = venue
    elif result["venues"]:
        result["venue"] = result["venues"][0]

    ftp = capacities.get("cycling_ftp_w")
    lthr = capacities.get("running_lthr_bpm")
    threshold_pace = capacities.get("running_threshold_sec_per_km")
    css = capacities.get("swim_css_sec_per_100m")
    for step in result["steps"]:
        if ftp and "ftp_pct" in step:
            lo, hi = step["ftp_pct"]
            step["target_watts"] = [_watts(ftp, lo), _watts(ftp, hi)]
        if step.get("target") == "threshold":
            if lthr:
                step["target_hr_bpm"] = [int(round(lthr * 0.96)), int(round(lthr * 1.01))]
            if threshold_pace:
                step["target_pace_sec_per_km"] = [int(round(threshold_pace - 5)), int(round(threshold_pace + 5))]
        if step.get("target") == "CSS" and css:
            step["target_sec_per_100m"] = [int(round(css - 2)), int(round(css + 2))]
    return result
