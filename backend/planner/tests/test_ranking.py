from datetime import datetime, timedelta, timezone

from planner.ranking import rank_routes
from planner.risk import LEVELS

DEPARTURE = datetime(2026, 11, 24, 14, 0, tzinfo=timezone.utc)


def route(route_id, *stretches, duration_s=36_000):
    """A route made of (level, miles) stretches, one checkpoint per stretch, at 60 mph."""
    checkpoints, mile = [], 0.0
    for level, miles in stretches:
        checkpoints.append(
            {
                "mile": mile,
                "eta": DEPARTURE + timedelta(hours=mile / 60),
                "segment_mi": miles,
                "level": level,
                "score": LEVELS.index(level),
            }
        )
        mile += miles
    return {"id": route_id, "distance_mi": mile, "duration_s": duration_s, "checkpoints": checkpoints}


def test_no_travel_miles_beat_everything():
    plan = rank_routes(
        [
            route("A", ("no_travel", 5), ("low", 95), duration_s=3_600),
            route("B", ("severe", 60), ("high", 40), duration_s=9_000),
        ]
    )

    assert [r["id"] for r in plan["routes"]] == ["B", "A"]
    assert [r["rank"] for r in plan["routes"]] == [1, 2]
    assert plan["recommended_route_id"] == "B"
    assert plan["recommendation_reason"] == "Route B: 0 No Travel miles vs 5 on Route A."
    assert plan["warnings"] == []


def test_a_route_summary_counts_miles_by_level_and_finds_the_first_hazard():
    (summary,) = (r["summary"] for r in rank_routes([route("A", ("low", 30), ("high", 20), ("severe", 10), ("low", 40))])["routes"])

    assert summary == {
        "miles_by_level": {"low": 70, "moderate": 0, "high": 20, "severe": 10, "no_travel": 0},
        "avg_risk": 0.7,  # (20 × 2 + 10 × 3) / 100
        "max_level": "severe",
        "first_hazard": {"mile": 30, "eta": DEPARTURE + timedelta(minutes=30), "level": "high"},
    }


def test_a_route_without_high_or_worse_has_no_first_hazard():
    plan = rank_routes([route("A", ("moderate", 50), ("low", 50))])

    assert plan["routes"][0]["summary"]["first_hazard"] is None
    assert plan["recommendation_reason"] == "Route A is the only route found."


def test_when_every_route_has_no_travel_the_least_bad_is_recommended_with_a_warning():
    plan = rank_routes([route("A", ("no_travel", 30), ("low", 70)), route("B", ("no_travel", 10), ("low", 90))])

    assert plan["recommended_route_id"] == "B"
    assert plan["warnings"] == ["Every route has No Travel miles. Consider delaying departure."]


def test_routes_tied_on_everything_keep_the_router_order():
    plan = rank_routes([route("A", ("low", 100)), route("B", ("low", 100))])

    assert plan["recommended_route_id"] == "A"
    assert plan["recommendation_reason"] == "Routes A and B tie on weather risk and travel time."


def test_severe_miles_beat_high_miles():
    plan = rank_routes([route("A", ("severe", 10), ("low", 90)), route("B", ("high", 80), ("low", 20))])

    assert plan["recommended_route_id"] == "B"
    assert plan["recommendation_reason"] == "Route B: 0 Severe miles vs 10 on Route A."


def test_high_miles_beat_average_risk():
    plan = rank_routes([route("A", ("high", 20), ("low", 80)), route("B", ("high", 12.5), ("moderate", 87.5))])

    assert plan["recommended_route_id"] == "B"
    assert plan["recommendation_reason"] == "Route B: 12.5 High miles vs 20 on Route A."


def test_with_equal_hazard_miles_the_lower_average_risk_wins():
    plan = rank_routes(
        [
            route("A", ("moderate", 61), ("low", 39), duration_s=3_600),
            route("B", ("moderate", 42), ("low", 58), duration_s=9_000),
        ]
    )

    assert plan["recommended_route_id"] == "B"
    assert plan["recommendation_reason"] == (
        "Routes B and A tie on No Travel, Severe and High miles; Route B has the lower average risk (0.42 vs 0.61)."
    )


def test_equal_rounded_average_risk_goes_to_the_faster_route():
    # Average risk 0.396 and 0.404: A is lower, but both round to 0.40, so the faster B wins.
    plan = rank_routes(
        [
            route("A", ("moderate", 39.6), ("low", 60.4), duration_s=10_000),
            route("B", ("moderate", 40.4), ("low", 59.6), duration_s=8_560),
        ]
    )

    assert plan["recommended_route_id"] == "B"
    assert plan["recommendation_reason"] == "Routes B and A have the same weather risk; Route B is 24 min faster."


def test_hazard_miles_within_float_noise_do_not_decide():
    # 20.04 and 20.0 High miles are both 20.0 at 0.1 mi, and the averages round to 0.40, so the faster A wins.
    plan = rank_routes(
        [
            route("A", ("high", 20.04), ("low", 79.96), duration_s=8_000),
            route("B", ("high", 20.0), ("low", 80.0), duration_s=9_000),
        ]
    )

    assert plan["recommended_route_id"] == "A"


def test_a_faster_route_by_under_a_minute_still_says_it_is_faster():
    plan = rank_routes([route("A", ("low", 100), duration_s=9_000), route("B", ("low", 100), duration_s=8_980)])

    assert plan["recommended_route_id"] == "B"
    assert plan["recommendation_reason"] == (
        "Routes B and A have the same weather risk; Route B is under a minute faster."
    )
