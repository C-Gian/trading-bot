from app.research.wp005_validation import validate_wp005


def test_wp005_static_checkpoint_validation():
    result = validate_wp005(data_available=False)
    assert result["status"] == "PASS"
    assert result["experiments"] == 9
    assert result["classification"] == "ALIGNED_DIAGNOSTIC_SUPPORTED_BUT_INCONCLUSIVE"
