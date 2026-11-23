from datetime import datetime, timedelta, timezone

from planner.eta import eta_at_mile

DEPARTURE = datetime(2026, 11, 24, 14, 0, tzinfo=timezone.utc)
MILE_M = 1609.344

# (cumulative offset in meters, cumulative travel time in seconds): 10 mi in 10 min, then 10 mi in 20 min.
INSTRUCTIONS = [(0, 0), (10 * MILE_M, 600), (20 * MILE_M, 1800)]


def test_eta_is_interpolated_between_the_bracketing_instructions():
    eta = eta_at_mile(15, DEPARTURE, INSTRUCTIONS, total_mi=20, total_s=1800)

    assert eta == DEPARTURE + timedelta(seconds=1200)


def test_ends_of_the_route_match_departure_and_the_last_instruction():
    assert eta_at_mile(0, DEPARTURE, INSTRUCTIONS, total_mi=20, total_s=1800) == DEPARTURE
    assert eta_at_mile(20, DEPARTURE, INSTRUCTIONS, total_mi=20, total_s=1800) == DEPARTURE + timedelta(minutes=30)


def test_without_instructions_time_is_proportional_to_distance():
    for instructions in ([], [(0, 0)]):
        eta = eta_at_mile(5, DEPARTURE, instructions, total_mi=20, total_s=1800)

        assert eta == DEPARTURE + timedelta(seconds=450)
