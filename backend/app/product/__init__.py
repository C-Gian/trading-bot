"""Local paper-research product surface.

This package is the only place where current (post-development-cutoff) BTCUSDT market
data is permitted, and only as prospective paper-research input. Nothing here writes to
the development store, fits a model, selects a parameter, produces a historical report,
or touches sealed evaluation. Results are transient.
"""

PRODUCT_ANALYSIS_VERSION = "PAPER_RESEARCH_ANALYSIS_V1"

__all__ = ["PRODUCT_ANALYSIS_VERSION"]
