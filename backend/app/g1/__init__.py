"""System G1 — Checkpoint-1 synthetic causal vertical slice (ADR-0044).

This package implements the frozen System G1 core contracts
(`research/protocols/SYSTEM-G1-CORE-CONTRACTS-V1.md`) on synthetic fixtures only. It contains no
fitted forecaster, no frozen P1/P2 trigger construction and no historical-market adapter; it never
reads BTC market data. Every run it can register is a synthetic fixture, not market evidence.
"""

GENERATION = "SYSTEM_G1"
ALGORITHM_VERSION = "SYSTEM_G1_CHECKPOINT_1_SYNTHETIC_CORE_V1"
SCHEMA_VERSION = "SYSTEM_G1_RECORDS_V1"
CORE_CONTRACT = "research/protocols/SYSTEM-G1-CORE-CONTRACTS-V1.md"
CYCLE_CONTRACT = "research/protocols/SYSTEM-G1-CYCLE-METHOD-V1.md"
REFERENCE_INSTRUMENT = "BTCUSDT_USDM_TRADED_PRICE_REFERENCE_PAPER"
DECISION_TIMEFRAME = "15m"
FORECAST_HORIZON_MINUTES = 240
EVIDENCE_CLASS = "SYNTHETIC_FIXTURE_NOT_MARKET_EVIDENCE"
