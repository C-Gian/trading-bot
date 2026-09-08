# Record keeping

`state/current_state.json` is the sole editable current state. Material decisions use ADRs; every completed work package gets one concise immutable checkpoint. Material experiments each occupy one directory and must be preregistered before execution. Terminal results are never rewritten; failures and negative results remain. Indexes link and summarize records. Canonical documents are not journals, verbose logs are not canonical history, and Git history is part of the audit trail.

