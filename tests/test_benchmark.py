from benchmarks.benchmark import percentile


def test_percentile_interpolates():
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.5) == 25.0
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.95) == 38.5
