from app.research.wp005_diagnostics import quantile_type7, random_gate_rank, random_gate_seed


def test_seed_derivation_is_frozen():
    assert random_gate_seed(0) == 11624029624526925664
    assert random_gate_seed(31) == 12258752712694973949
    assert len({random_gate_seed(index) for index in range(32)}) == 32


def test_rank_uses_seed_and_integer_timestamp_only():
    assert random_gate_rank(1, 2).hex() == random_gate_rank(1, 2).hex()
    assert random_gate_rank(1, 2) != random_gate_rank(2, 1)


def test_type7_quantile_is_linear_and_deterministic():
    values = list(range(32))
    assert quantile_type7(values, 0.1) == 3.1
    assert quantile_type7(values, 0.5) == 15.5
    assert quantile_type7(values, 0.9) == 27.9
