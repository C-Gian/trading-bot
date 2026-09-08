# Phase 0 architecture

React calls versioned FastAPI routes. Thin routes delegate to Python application/data modules. Python owns all authoritative quantitative behavior. Parquet is local history storage. V1 binds only to localhost and contains no execution or credentials path.

