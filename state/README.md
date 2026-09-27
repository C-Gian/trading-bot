# State

`current_state.json` is the single machine-readable project-state file used by the application.

For human/agent bootstrap, read **only the leading `current_project_status` block first**. The file is intentionally ordered so current truth appears before large historical compatibility fields.

Read additional top-level fields only when a specific runtime, lineage or audit task requires them.
