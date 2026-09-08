# Time-series evaluation V1

Evaluation uses chronological train/development then validation windows. Each fold has exact UTC boundaries, a horizon-aware purge before validation and an embargo after it. Fold construction rejects overlap and dates beyond the development cutoff. Random K-fold is prohibited.

Future preregistrations must set purge and embargo from feature lookback and label/holding horizon. The sanctioned signal interface exposes only completed 1h/4h bars available as of signal time. The execution path is provided only after the intent is frozen.

Invalid and unresolved trades are always counted separately. Each future experiment must preregister how they enter its primary-metric denominator.
