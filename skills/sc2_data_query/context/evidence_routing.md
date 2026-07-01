# Evidence Routing

Semantic relations can point to exact copied Markdown evidence.

1. Keep `relation_id` from relation results.
2. Inspect its `fact` array or call `query_relation_evidence`.
3. Use the fact's release-relative `document`, `line_start`, and `line_end` with `read_markdown_evidence`.
4. Cite the path and lines in the final answer.

Use `resolve_markdown_documents` when starting from an entity name. Use `search_markdown` when no structured field or relation directly represents the requested fact. Never construct arbitrary filesystem paths.
