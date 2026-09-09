from __future__ import annotations

import numpy as np
import pytest
from app.research.linear_model import LinearModelError, fit_ols


def test_ols_uses_training_only_scaling_and_reproduces_linear_target() -> None:
    x = np.asarray([[1.0, 2.0], [2.0, 1.0], [3.0, 4.0], [4.0, 3.0]])
    y = 0.5 + 2.0 * x[:, 0] - 0.25 * x[:, 1]
    model = fit_ols(
        x,
        y,
        ("F1", "F2"),
        training_matrix_hash="a" * 64,
        training_label_hash="b" * 64,
        dependency_hash="c" * 64,
    )
    assert model.rank == 3
    assert model.means.tolist() == [2.5, 2.5]
    assert np.allclose(model.predict(x), y)
    assert model.as_record()["regularization"] == "NONE"
    assert model.as_record()["signal_threshold"] == 0.0


def test_ols_rejects_zero_variance_and_rank_deficiency() -> None:
    with pytest.raises(LinearModelError, match="standard deviation"):
        fit_ols(
            np.ones((4, 1)),
            np.arange(4.0),
            ("F1",),
            training_matrix_hash="a",
            training_label_hash="b",
            dependency_hash="c",
        )
    with pytest.raises(LinearModelError, match="full column rank"):
        fit_ols(
            np.asarray([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0]]),
            np.arange(4.0),
            ("F1", "F2"),
            training_matrix_hash="a",
            training_label_hash="b",
            dependency_hash="c",
        )
