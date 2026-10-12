# Pre-registration A6: final grid on benchmark v0.2 (frozen 12 Oct 2026, before any Sonnet or Opus call and before any Haiku call on the final split)

Questions: `data/benchmark/questions.jsonl` (119; Q1 14, Q2 10, Q3 44 incl. 12 cohort-level, Q4 30, Q7 21), gold by plain Python on `data/release/`. Splits: dev 20, selection 29 (used for development and bug fixes with Haiku, 1 repeat), final 70 (not run before this document). No question, prompt, tool or scorer change after the first final-split call; a bug fix means the whole grid is rerun.

## What runs
| Model | Systems | Questions | Repeats |
| --- | --- | --- | --- |
| claude-haiku-5-5 | A, A+, C, D, E | all 119 (final split is the headline) | 3 |
| claude-sonnet-5-5 | A, C, D, E | final split (70) | 1 |
| claude-opus-5-5 | A, C, D, E | fixed half of the final split (every second question per family, id order) | 1 |
E is not applicable to the cohort-level questions. A+ (noise rule added) is run on Haiku only. Effort `medium`, no sampling parameters, tool choice automatic, answers by JSON schema, every response cached in `runs/`.

## Outcomes
Primary: share of questions answered correctly (every gold field matches; abstain matches), on the final split. Secondary: by family and by template; by step count; cost in USD per question; tool calls and turns; failure type (wrong field, wrong abstention, missing answer, error).

## Analysis
Athlete-clustered bootstrap (2000 resamples, seed 1; each cohort-level question is its own cluster). Paired differences between systems on the same questions. A separation between two systems is claimed only if the 95% interval of the paired difference excludes 0. Per-model results are reported separately; no pooled claim across models.

## Expectations (stated before the run)
- H1: on cohort-level (aggregation) questions the single call A is below both agent systems C and D for every model.
- H2: on Q1, Q2, Q4 and Q7 all systems are within 5 percentage points of each other (ceiling).
- H3: D is within 3 points of C and costs at least 1.4 times as much.
- H4: E matches C on per-athlete questions.
- H5: A+ equals A on Q4 for Haiku.
Results are reported whichever way they fall.

## Limits
One cohort, one sport, one test; one vendor; 70 final questions (7 cohort-level); questions about the same athlete are correlated; the noise estimate comes from 2 to 3 trials per test; gold for noise questions uses one convention (95% reliable change).

## Addendum (12 Oct 2026, after the grid)
1. Code edited during the run: the runner (cache directory setting, optional tracing hook), `config.py` (runs directory, centile grid moved to `data/norm_grid/`), the centile tool (imports the grid path from config) and optional `max_tokens` / `max_turns` parameters of systems A and C (defaults unchanged). Prompts, tool definitions, scoring and questions were not changed.
2. Post hoc and declared after seeing results: (a) re-run of the 59 capped runs with 16,000 tokens and 16 turns (`runs_sensitivity/capped_reruns.jsonl`); it repeats only capped runs, so it can raise accuracy and never lower it; (b) designed sweep of the output cap for system A on the 12 cohort-level questions (`runs_sensitivity/capsweep.jsonl`, caps 2000, 4000, 8000, 16000).
3. Cost: cached input of system A is billed at 10 percent of the input price in our code; the published cache-read price for Opus 5.5 is lower (5 percent), so the Opus cost of A is somewhat overstated. Cost ratios between C, D and E are exact (no caching). D versus E is computed on the 62 per-athlete questions both answer.
4. Q4 finding: in the final split 4 of 15 Q4 questions lie between half and one times the reliable change; all systems answered them correctly. System A sees the trial table and can estimate noise itself, so Q4 does not probe the implicit-threshold effect of the earlier exploratory studies.
