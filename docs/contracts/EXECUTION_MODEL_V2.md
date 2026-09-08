# Execution model V2

Version: `EXECUTION_MODEL_V2`.

After continuity is established for each canonical minute: (1) an open below stop exits at that adverse open; (2) an open at or above target exits at the conservative target price; (3) intrabar stop and target touches resolve stop first when both are possible; (4) a lone stop or target touch uses its trigger price. Expiry and unresolved policies remain as prospectively defined in V1. This ordering makes an available target at the open causally prior to later intrabar movement.

Strategy lookbacks are sorted, UTC-aligned, duplicate-free contiguous complete suffixes. A request returns exactly the requested count or declares the clock ineligible. No missing or partial interval is manufactured.
