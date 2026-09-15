# CURRENT TASK — P0.1-DETECTABILITY-INFERENCE-AND-CI-PORTABILITY-FIX

Status: CORRECTION_REQUIRED_AFTER_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `a8e54d472add9d9257e7073c2b6c9258012884c2` on local `main`.

Correct two bounded P0 blockers without executing a market experiment or changing any
historical result:

1. make statistical artifact reconstruction byte-identical across supported clean
   environments using a governed frozen numerical dependency identity and a
   platform-stable reduction path;
2. prevent positive-ACF trade ESS diagnostics from serving as an inferential MDE basis.

Historical diagnostic ESS remains reportable only as a diagnostic. Historical MDE must
fail closed with `NO_GOVERNED_INFERENTIAL_DEPENDENCE_MODEL` when no governed inferential
dependence model exists. Naive IID statistics remain explicitly labelled, and historical
classifications remain immutable.

P0 status may become ACCEPTED only after full local validation and exact-head GitHub
Actions SUCCESS. No P1A, sealed evaluation, market experiment, or real-money work is in
scope.
