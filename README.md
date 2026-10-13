# lcb: a small benchmark of LLM systems on longitudinal athlete jump-test data

This repository accompanies an anonymous submission. It contains the benchmark (questions, gold answers, de-identified data), the five systems that are compared, the scorer, the analysis code and the cached model responses, so that every result table and plot can be rebuilt without an API key.

## What is compared

Letters below are the repository's. The paper relabels the systems as A, B (agent, C here), C (multi-agent, D here) and D (fixed pipeline, E here); B here is a retrieval baseline that the paper does not use. A+ (A with the noise rule added, run with Haiku only) is in the repository and in the cached runs but is not reported in the paper.

Question families: the paper labels them Q1 lookup, Q2 centile, Q3 longitudinal, Q4 cohort-level, Q5 noise and Q6 edge cases; the repository's `family` field uses Q1, Q2, Q3 (including cohort-level questions, tagged `cohort`), Q4 (noise) and Q7 (edge cases).

Five ways of answering a coach's question about football countermovement-jump (CMJ) tests with one Claude model each time:

| ID | System |
| --- | --- |
| A | one call; the data table, the centile grid and the trial table are in the prompt, no noise information |
| A+ | A plus the cohort measurement-noise rule |
| C | one agent with three tools (`sql`, `centile`, `tracking`) |
| D | a coordinator that delegates to a data specialist and a statistics specialist |
| E | fixed code builds an evidence bundle for the athlete named in the question, one call writes the answer |

Questions come in five families: Q1 numerical lookups, Q2 centile position, Q3 longitudinal and cohort-level questions, Q4 change versus measurement noise, Q7 edge cases (missing athlete, missing test, one test only, missing trial, outside the reference range). Gold answers are computed by plain Python on the released tables; no model is used as a judge.

## Layout

```text
src/lcb/            package: config, tools, llm client, benchmark (generator, gold, scorer), systems, runner, analysis, experiments
src/lcb/legacy/     scripts of the exploratory studies on real consecutive test pairs (Appendix G of the paper); they read private files (data_private/) that are not released, so they document the method but cannot be rerun here
data/release/       de-identified tests and trials tables (pseudonymous athlete ids; no names, no club)
data/benchmark/     questions.jsonl, inventory.csv
data/norm_grid/     centile lookup grid and its provenance
centile_model/      R script that fits the centile model and writes the grid (needs the full database for the shipped grid; see data/norm_grid/PROVENANCE.md)
runs/               cached responses of every system and model (one JSONL file per system and model)
results/            aggregate result tables and plots (results/exploratory: outputs of the exploratory studies, Appendix G)
tests/              unit tests (tools, release view, benchmark integrity)
docs/               data statement, reproduction notes, pre-registered analysis plans (ANALYSIS_*.md)
```

## Reproduce

```bash
make install          # editable install with test dependencies
make test             # unit tests, no key and no network
make tables           # rebuild the result tables and plots in results/ from the cached responses in runs/ (no API calls)
make questions        # regenerate the benchmark from data/release (deterministic, seed 11)
```
To rerun a system yourself, put `ANTHROPIC_API_KEY` in a `.env` file and use `make run SYSTEM=C MODEL=haiku SPLIT=final`. The runner is resumable, caches every response, and stops at a cost cap. Hosted models can change; the cached responses are the record of what was measured, with the model identifiers and dates in `runs/`.

## Data and licences
Code: Apache-2.0. Tables, questions and cached responses: CC BY-NC 4.0 (see `docs/DATA_STATEMENT.md`). The tables describe real athletes, among them children, with names, club and the original profile identifiers removed. Please read the data statement before using them.
