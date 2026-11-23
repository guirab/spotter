from pytest import approx

from planner.geo import sample_checkpoints

# Along the equator one degree of longitude is 2π × 3958.8 mi / 360 (mean Earth radius).
MI_PER_DEG = 69.0934


def equator_line(*miles):
    """A [lon, lat] polyline along the equator with vertices at the given miles from lon 0."""
    return [[m / MI_PER_DEG, 0.0] for m in miles]


def test_non_exact_multiple_ends_with_a_short_destination_segment():
    checkpoints = sample_checkpoints(equator_line(0, 60, 110), interval_mi=25)

    assert [c["mile"] for c in checkpoints] == approx([0, 25, 50, 75, 100, 110], abs=0.01)
    assert [c["segment_mi"] for c in checkpoints] == approx([12.5, 25, 25, 25, 17.5, 5], abs=0.01)


def test_exact_multiple_has_no_extra_destination_checkpoint():
    checkpoints = sample_checkpoints(equator_line(0, 100), interval_mi=50)

    assert [c["mile"] for c in checkpoints] == approx([0, 50, 100], abs=0.01)
    assert [c["segment_mi"] for c in checkpoints] == approx([25, 50, 25], abs=0.01)


def test_checkpoints_are_interpolated_along_the_line():
    # 60 mi east along the equator, then 60 mi north.
    corner = 60 / MI_PER_DEG
    checkpoints = sample_checkpoints([[0, 0], [corner, 0], [corner, corner]], interval_mi=25)

    assert [(c["lon"], c["lat"]) for c in checkpoints] == [
        approx((0, 0)),
        approx((25 / MI_PER_DEG, 0), abs=1e-4),
        approx((50 / MI_PER_DEG, 0), abs=1e-4),
        approx((corner, 15 / MI_PER_DEG), abs=1e-4),
        approx((corner, 40 / MI_PER_DEG), abs=1e-4),
        approx((corner, corner)),
    ]
