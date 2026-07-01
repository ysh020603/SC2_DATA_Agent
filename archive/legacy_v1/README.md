# Legacy SC2 Data Agent Archive

This directory preserves files from the pre-2026-07-01 runtime for historical reference only.

The archived database, builder, schema document, search-tool document, provider example, and old Streamlit output files are not imported or loaded by the current application. The active runtime uses `data_sc2_260701`, `API_Tools`, and `API_config` from the repository root.

The former real provider configuration is stored locally under `private/` and is excluded from Git because it may contain credentials.

Do not copy legacy paths or relation names back into the current runtime. In particular, the old `hard_counters` and `soft_counters` relations were replaced by the unified `counters` relation.
