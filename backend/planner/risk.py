"""Checkpoint risk from weather and load, per the brief's table (PLAN.md §4.1)."""

from operator import ge, gt

LEVELS = ["low", "moderate", "high", "severe", "no_travel"]  # index = score
LABELS = ["Low", "Moderate", "High", "Severe", "No Travel"]

# Entry into Moderate, High, Severe and No Travel, with the brief's operators.
CONDITIONS = [
    # (weather key, name, unit,  Moderate     High         Severe       No Travel)
    ("wind_mph", "Wind", "mph", [(ge, 25), (ge, 35), (ge, 45), (ge, 55)]),
    ("rain_in_hr", "Rain", "in/h", [(ge, 0.10), (ge, 0.25), (ge, 0.50), (gt, 1.00)]),
    ("snow_in_hr", "Snow", "in/h", [(ge, 0.5), (ge, 1.0), (ge, 2.0), (gt, 3.0)]),
]

# Raise the level when the load is heavy for the wind. Wind ≥ 55 mph is already No Travel in the table.
LOAD_RULES = [
    # (wind from, wind below, load above, raised to, rule)
    (45, 55, 30_000, "no_travel", "45–54 mph & >30,000 lb"),
    (35, 45, 40_000, "severe", "35–44 mph & >40,000 lb"),
]


def classify(weather, load_lb):
    """{level, score, reasons} for one checkpoint's weather and the truck's load.

    The level is the worst of wind (sustained, not gusts), rain and snow.
    """
    score, reasons = 0, []
    for key, name, unit, thresholds in CONDITIONS:
        value = weather[key]
        condition_score = sum(op(value, bound) for op, bound in thresholds)
        if condition_score:
            reasons.append(f"{name} {value:g} {unit} → {LABELS[condition_score]}")
        score = max(score, condition_score)
    for wind_from, wind_below, load_above, raised_to, rule in LOAD_RULES:
        raised = LEVELS.index(raised_to)
        if wind_from <= weather["wind_mph"] < wind_below and load_lb > load_above and raised > score:
            score = raised
            reasons.append(f"Load rule: {rule} → {LABELS[raised]}")
    return {"level": LEVELS[score], "score": score, "reasons": reasons}
