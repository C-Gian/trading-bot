# SEARCH_MEMORY_V2 supervised-model extension

Status: accepted prospectively for WP-008 and later model proposals. The frozen
SEARCH_MEMORY_V2 strategy-spec implementation and all historical hashes remain
unchanged.

Every supervised model proposal is bound before results to an executable model spec
containing the algorithm, label and isolation semantics, ordered features and exact
transformations, chronological train-window/purge rule, scaling scope and convention,
regularization, all hyperparameters and their search count, signal comparison and
threshold, execution geometry, dataset/cost/execution versions, and implementation and
config dependency hashes.

The canonical fingerprint hashes all of those scientific fields. Its structural hash
masks numeric values, so a threshold, purge, hyperparameter, barrier, or horizon change
within an existing root is detected as parameter drift rather than a new family. An
exact hash collision is a duplicate. Other changes inside an admitted root are
descendants and require explicit remaining budget. Annual fitted coefficient vectors
are model outputs and never separate hypotheses.

WP-008 uses this additive extension because modifying the historical strategy-spec
module would invalidate prior preregistration dependency identities.
