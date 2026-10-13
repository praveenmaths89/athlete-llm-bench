# Reproduction notes

1. `make install && make test` checks the tools, the release view and the benchmark integrity.
2. `make tables` rebuilds the result tables and plots in `results/` from `runs/*.jsonl` without any API call.
3. `make questions` regenerates `data/benchmark/questions.jsonl` from `data/release/` (deterministic). The split of a question depends on its athlete (a hash of the pseudonymous id); cohort-level questions are assigned by a hash of the question id.
4. A rerun of a system needs an Anthropic API key. Sampling parameters cannot be set on the models used, so repeated runs vary; the paper reports the cached runs.
5. The noise estimate used by the benchmark (`results/typical_error.json`) was computed from within-test trial spread in the source extract before de-identification (male 3.63 cm, female 5.45 cm). `python -m lcb.tools.noise_estimate` recomputes it from the released tables and prints both; the released tables give slightly different values (about 3.71 and 5.27 cm) because they are a de-identified rebuild with a few tests fewer. The stored values are the ones in force for every question and answer in the benchmark.
