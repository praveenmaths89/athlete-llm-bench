# Reproduction notes

1. `make install && make test` checks the tools, the release view and the benchmark integrity.
2. `make tables` rebuilds the result tables and plots in `results/` from `runs/*.jsonl` without any API call.
3. `make questions` regenerates `data/benchmark/questions.jsonl` from `data/release/` (deterministic). The split of a question depends on its athlete (a hash of the pseudonymous id); cohort-level questions are assigned by a hash of the question id.
4. A rerun of a system needs an Anthropic API key. Sampling parameters cannot be set on the models used, so repeated runs vary; the paper reports the cached runs.
5. The noise estimate (`results/typical_error.json`) comes from within-test trial spread; the trial table is released, so it can be recomputed with `python -m lcb.tools.noise_estimate`.
