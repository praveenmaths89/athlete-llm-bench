# Pre-registration A5: does showing a centile movement cause "real change" verdicts? (frozen 11 Oct 2026, before any A5 call)

Status of earlier work: A1 to A4 were each specified after seeing earlier output and are EXPLORATORY. A5 is the only confirmatory test. No prompt, schema, design or analysis edit after the first A5 call; bugs are fixed and the whole run repeated.

## Question
Holding the jump values, sex, baseline centile and time gap fixed, does displaying a larger centile movement raise the share of answers that call a within-noise jump change "real"?

## Why synthetic and on-grid
In real pairs the centile movement and the size of the change rise together (confounded; GEE coefficient for centile movement not significant once the change is controlled). Synthetic athletes built from the published GAMLSS grid allow independent manipulation, stay consistent with the real centile model, and contain no real child's data.

## Design (180 cells, each with a with-centile and a no-centile twin)
- sex: Male, Female; age at test 1: 10, 12, 14, 16, 20 years; test 2 is 0.5 years later (stated as 6 months).
- baseline centile of test 1: 25, 50, 75 (jump value 1 = grid value at that age and centile, rounded to 0.1 cm).
- change size: 1.5, 2.5, 3.2 cm, direction up or down (value 2 = value 1 +/- size, rounded to 0.1 cm). All sizes are below the cohort 95% reliable change (male 3.63 cm, female 5.45 cm), so the gold verdict of every cell is within measurement noise.
- the centile shown for test 2 comes from the centile tool at age + 0.5; the movement therefore varies with age (the distribution is narrower in children) while the jump values stay fixed. Centile movement `delta` = displayed centile 2 minus displayed centile 1 (integers).
- twin: shown = 1 includes the centile line, shown = 0 omits it; everything else identical. The twin removes any direct effect of age and baseline from the contrast.
- cells whose centile falls outside P3 to P97 at either test are dropped and counted.
- feasibility (local, before freezing): at a fixed change the movement for falls varies by about 10 to 15 centile points across ages (male -1.5 cm: -10.9 to -24.3; -2.5 cm: -16.5 to -31.4); for rises the spread is smaller (about 3 to 5 points). Hence **falls are the primary test, rises secondary**.

## Models and runs
claude-haiku-5-5 and claude-sonnet-5-5: 2 runs per prompt (confirmatory). claude-opus-5-5: 1 run, only if credit is confirmed (confirmatory if run). Effort medium; no sampling parameters; JSON schema output; same system line and instruction for both twins (the instruction says centile_change_reason is `none` when no centile is given).

## Outcome
Primary: Y = 1 if `jump_change_is` = real. Reported alongside: shares of within_measurement_noise and cannot_tell (a drop in "real" could be a rise in hedging).

## Primary analysis (falls only, per model)
1. GEE logistic (cluster = cell): Y ~ shown + z + shown:z + size + female + age + baseline, with z = |delta| / 10. **Primary parameter: the coefficient of shown:z.**
2. Contrast: mean Y(shown) minus mean Y(not shown), within tertiles of |delta| among falls, with cell-clustered bootstrap 95% intervals (2000 resamples, seed 1).
3. Holm correction over the two confirmatory models (Haiku, Sonnet).

## Decision rules (fixed now)
- Contamination supported for a model: shown:z coefficient positive with 95% interval excluding 0 AND top-tertile contrast >= 10 percentage points.
- Null for a model: shown:z interval includes 0 AND |top-tertile contrast| < 5 points. With 90 fall cells x 2 runs the interval for a 10-point effect is expected to exclude 0; a wider interval is reported as inconclusive.
- Anything else: inconclusive, reported as such.

## What the paper claims
- Supported in both confirmatory models: "Displaying the centile movement causally inflates 'real change' verdicts for within-noise changes."
- Null in both: "At fixed change size, the displayed centile movement did not affect verdicts; the association in real pairs was due to the size of the change. The contribution is the implicit, cohort-independent noise threshold and its fix."
- Mixed: report per model; no pooled claim.

## Secondary (exploratory)
Rises; direction alignment of jump change and centile; `centile_change_reason`; stated `noise_threshold_cm` with and without the centile; the same contrast at the model's own implicit threshold.

## Limits stated in advance
Synthetic vignettes; one test and sex pair of cohorts from one pooled grid; one vendor; 6-month gaps only; the centile shown is from the in-sample grid.
