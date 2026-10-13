# Centile grid

`cmj_jump_height_centile_grid.csv`: reference centiles (P3, P10, P25, P50, P75, P90, P97) of impulse-momentum countermovement-jump height (cm), by sex and age in 0.5-year steps. They come from the centile model of this study: a GAMLSS model fitted separately for each sex to the full countermovement-jump database (767 tests, 530 athletes; 576 male tests of 410 athletes and 191 female tests of 120 athletes). The fitting code is `centile_model/fit_centiles.R`. The database itself is not released, so the grid is shipped as a lookup table and used as such by the benchmark tools.

Running `Rscript centile_model/fit_centiles.R data/release/tests.csv grid.csv` fits the same model to the released football tests only (408 tests). Its centiles are close to, not identical with, the shipped grid (on the shared ages the median differs by 0.8 cm on average); the shipped grid is the one used for every question and answer in the benchmark.

Columns are test_type, gender, variable, age, P3..P97, n_tests, n_athletes, sample_label, expected_se_z_p3. The centiles are in-sample with respect to the athletes in the benchmark (stated in the paper's Limitations).
