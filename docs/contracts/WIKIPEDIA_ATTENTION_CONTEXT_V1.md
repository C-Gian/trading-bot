# Wikipedia Attention Context V1

The sole source is the official Wikimedia REST Pageviews API using exactly
`en.wikipedia / Bitcoin / all-access / user / daily`. Acquisition begins at the API's
pageview-series inception on 2015-07-01 and ends at 2024-12-31. Requests, raw response
bytes, metadata, hashes, canonical daily rows, and gap/duplicate audits are preserved.

For UTC day D, an observation is available to the hourly research substrate only at the
first hourly boundary after `end_of_day(D) + 24 hours`, equivalently day-start D + 48
hours. Same-day and next-day-before-completion use are forbidden. Missing daily source
observations are never interpolated and make the dependent context unavailable.

`BITCOIN_WIKIPEDIA_ATTENTION_SHOCK_V1` is exactly
`log((pageviews_D + 1) / (median(previous 28 daily pageviews) + 1))`. D is excluded from
the median; all 28 preceding daily observations must exist consecutively. There is no
alternative article, language, access class, agent class, window, clipping, scaling,
threshold, or second attention feature.

This is predictive public-attention context, not a causal or sentiment-truth claim.
