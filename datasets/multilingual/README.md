# Multilingual synthetic gold v1

120 additional DE/FR/IT cases. No real insurance documents or personal data.
Source documents and expected labels are single-author synthetic annotations; zero
independent professional reviews. Dev/holdout families and templates are disjoint.
Freeze binds exact file bytes and canonical model hash plus the 24 pilot IDs.

Build authoring source: scripts/build_multilingual_gold.py. Do not regenerate v1 after
live measurement; changes need a new gold/freeze version. The runtime gives only Source
to the renderer and only verified context to providers. No labels are sent to models.

See docs/REAL_LLM_BENCHMARK.md for assumptions, rates, splits and metrics. Generated
PDFs and run outputs belong under ignored datasets/evaluation-real, not in Git.
