"""G2-02 exposed development batch (baseline, fixed references, predeclared diagnostic ablations).

The frozen G2-01 modules (`app.g2.core`, `models`, `distribution`, ...) are not modified: their
canonical hashes are bound by the Gate-B engineering validation artifact. This package adds a
subclass of the frozen core whose decision/refit path is verified byte-identical to `G2Core` for
the unmodified G2-V0 system on the synthetic engineering path, plus the deterministic scorer,
uncertainty report and autopsy.
"""
