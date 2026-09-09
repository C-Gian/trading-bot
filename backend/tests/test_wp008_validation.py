from app.research.wp008_validation import validate_wp008


def test_completed_wp008_checkpoint_is_structurally_valid() -> None:
    assert validate_wp008()["status"] == "PASS"
