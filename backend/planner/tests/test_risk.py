import pytest

from planner.risk import classify


def weather(wind=0.0, rain=0.0, snow=0.0):
    return {"wind_mph": wind, "gust_mph": wind + 10, "rain_in_hr": rain, "snow_in_hr": snow}


@pytest.mark.parametrize(
    "wind, level",
    [
        (24.9, "low"),
        (25, "moderate"),
        (34.9, "moderate"),
        (35, "high"),
        (44.9, "high"),
        (45, "severe"),
        (54.9, "severe"),
        (55, "no_travel"),
    ],
)
def test_wind_boundaries(wind, level):
    assert classify(weather(wind=wind), load_lb=0)["level"] == level


@pytest.mark.parametrize(
    "rain, level",
    [(0.0999, "low"), (0.10, "moderate"), (0.25, "high"), (0.50, "severe"), (1.00, "severe"), (1.0001, "no_travel")],
)
def test_rain_boundaries(rain, level):
    assert classify(weather(rain=rain), load_lb=0)["level"] == level


@pytest.mark.parametrize(
    "snow, level",
    [(0.49, "low"), (0.5, "moderate"), (1.0, "high"), (2.0, "severe"), (3.0, "severe"), (3.01, "no_travel")],
)
def test_snow_boundaries(snow, level):
    assert classify(weather(snow=snow), load_lb=0)["level"] == level


def test_the_worst_condition_sets_the_level():
    result = classify(weather(wind=10, snow=1.5), load_lb=0)

    assert (result["level"], result["score"]) == ("high", 2)
    assert result["reasons"] == ["Snow 1.5 in/h → High"]


@pytest.mark.parametrize(
    "wind, load_lb, level",
    [
        (40, 40_000, "high"),
        (40, 40_001, "severe"),
        (50, 30_000, "severe"),
        (50, 30_001, "no_travel"),
        (30, 80_000, "moderate"),
        (60, 0, "no_travel"),
    ],
)
def test_load_rules(wind, load_lb, level):
    assert classify(weather(wind=wind), load_lb)["level"] == level


def test_reasons_name_the_load_rule_that_raised_the_level():
    result = classify(weather(wind=38), load_lb=45_000)

    assert result["reasons"] == ["Wind 38 mph → High", "Load rule: 35–44 mph & >40,000 lb → Severe"]


def test_a_load_rule_never_lowers_the_level():
    result = classify(weather(wind=40, rain=1.5), load_lb=45_000)

    assert result["level"] == "no_travel"
    assert not any("Load rule" in r for r in result["reasons"])


def test_severe_rain_with_a_wind_load_no_travel_is_no_travel():
    result = classify(weather(wind=50, rain=0.6), load_lb=35_000)

    assert result["level"] == "no_travel"
    assert result["reasons"][-1] == "Load rule: 45–54 mph & >30,000 lb → No Travel"


def test_scores_run_from_low_0_to_no_travel_4():
    assert classify(weather(), load_lb=0)["score"] == 0
    assert classify(weather(wind=60), load_lb=0)["score"] == 4
