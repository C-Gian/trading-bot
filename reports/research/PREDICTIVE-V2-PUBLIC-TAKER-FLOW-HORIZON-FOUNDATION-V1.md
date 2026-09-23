# PREDICTIVE V2 PUBLIC TAKER FLOW HORIZON FOUNDATION V1 — result

Experiment: `EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION`
Protocol: `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md` (sha256 `6fb5da71b18a44bd6c8891f50b0490311f48a988eef27ea46ff66546762fe012`)
Source manifest: `data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json` (sha256 `cf696350cfe6294ffcbb74bef657ba9e58be22d232e7aab30c9cc7aa4c204bc4`)

**Selection: `FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY`**

| Horizon | Scored rows | Coverage | Model Brier | Control Brier | Improvement | Adjusted interval | Model log loss | Control log loss | AUC | Classification |
|---|---|---|---|---|---|---|---|---|---|---|
| 24h | 34997 | 0.9999 | 0.255469 | 0.251756 | -0.0037126 | [-0.0059875, -0.0013780] | 0.704701 | 0.696700 | 0.5046 | FOUNDATION_SIGNAL_NOT_SUPPORTED |
| 4h | 35017 | 0.9999 | 0.250464 | 0.250246 | -0.0002184 | [-0.0007812, 0.0003397] | 0.694102 | 0.693641 | 0.5177 | FOUNDATION_SIGNAL_NOT_SUPPORTED |
| 1h | 35030 | 0.9999 | 0.249381 | 0.250025 | 0.0006438 | [0.0001705, 0.0011318] | 0.691924 | 0.693197 | 0.5316 | FOUNDATION_SIGNAL_SUPPORTED |

## 24h

| Fold | Scored | Coverage | Base rate | Brier improvement | AUC |
|---|---|---|---|---|---|
| 2021 | 8722 | 0.9995 | 0.5807 | -0.0159943 | 0.4983 |
| 2022 | 8760 | 1.0000 | 0.5518 | 0.0048375 | 0.5176 |
| 2023 | 8756 | 1.0000 | 0.5241 | -0.0034666 | 0.5145 |
| 2024 | 8759 | 0.9999 | 0.5245 | -0.0002797 | 0.5155 |

Criteria:
- pooled_feature_coverage_at_least_0_95: PASS
- every_fold_feature_coverage_at_least_0_90: PASS
- pooled_brier_improvement_positive: FAIL
- adjusted_bootstrap_lower_bound_positive: FAIL
- at_least_3_of_4_folds_non_negative: FAIL
- pooled_log_loss_not_worse_than_control: FAIL

## 4h

| Fold | Scored | Coverage | Base rate | Brier improvement | AUC |
|---|---|---|---|---|---|
| 2021 | 8723 | 0.9995 | 0.5360 | -0.0026821 | 0.5138 |
| 2022 | 8760 | 1.0000 | 0.5215 | 0.0005898 | 0.4854 |
| 2023 | 8754 | 1.0000 | 0.5133 | 0.0011151 | 0.5408 |
| 2024 | 8780 | 0.9999 | 0.5122 | 0.0000936 | 0.5290 |

Criteria:
- pooled_feature_coverage_at_least_0_95: PASS
- every_fold_feature_coverage_at_least_0_90: PASS
- pooled_brier_improvement_positive: FAIL
- adjusted_bootstrap_lower_bound_positive: FAIL
- at_least_3_of_4_folds_non_negative: PASS
- pooled_log_loss_not_worse_than_control: FAIL

## 1h

| Fold | Scored | Coverage | Base rate | Brier improvement | AUC |
|---|---|---|---|---|---|
| 2021 | 8731 | 0.9995 | 0.5183 | -0.0010323 | 0.5094 |
| 2022 | 8760 | 1.0000 | 0.5114 | 0.0008187 | 0.5481 |
| 2023 | 8757 | 1.0000 | 0.5067 | 0.0016493 | 0.5526 |
| 2024 | 8782 | 0.9999 | 0.5084 | 0.0011330 | 0.5400 |

Criteria:
- pooled_feature_coverage_at_least_0_95: PASS
- every_fold_feature_coverage_at_least_0_90: PASS
- pooled_brier_improvement_positive: PASS
- adjusted_bootstrap_lower_bound_positive: PASS
- at_least_3_of_4_folds_non_negative: PASS
- pooled_log_loss_not_worse_than_control: PASS

Prediction-only foundation: no action threshold, trading PnL, costs, magnitude or sealed data. Champion NONE. Real money false.
