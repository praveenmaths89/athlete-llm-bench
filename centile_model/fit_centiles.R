# -----------------------------------------------------------------------------
# fit_centiles.R -- fit the sex-specific centile model of countermovement-jump
# height and write the centile grid used as a lookup by the benchmark.
#
# Model: for each sex, jump height Y at age a follows one of seven candidate
# distributions (NO, GA, LOGNO, WEI, BCCG, BCT, BCPE); the median and the spread
# are penalised B-splines of sqrt(age) with `knots` intervals, the skewness is a
# constant or a smooth function of age (1-5 df), and the tail weight is constant.
# The distribution and the skewness df are chosen by the Schwarz criterion
# (GAIC with penalty log n). Centiles P3-P97 are written on a 0.5-year age grid.
#
# Input : a CSV with columns  sex (Male/Female), age_years, jump_height_cm
#         (one row per test). The benchmark's grid was fitted on the full
#         countermovement-jump database (767 tests, 530 athletes), which is not
#         released; running this script on data/release/tests.csv fits the same
#         model to the released football tests only and gives a similar, not an
#         identical, grid.
# Output: a CSV in the format of data/norm_grid/cmj_jump_height_centile_grid.csv.
#
# Usage : Rscript centile_model/fit_centiles.R <input.csv> <output.csv>
#         (needs the R packages gamlss, dplyr, purrr, tidyr, tibble, readr)
# -----------------------------------------------------------------------------
suppressPackageStartupMessages({ library(gamlss); library(dplyr); library(purrr); library(tidyr); library(tibble); library(readr) })

args <- commandArgs(trailingOnly = TRUE)
input  <- if (length(args) >= 1) args[1] else "data/release/tests.csv"
output <- if (length(args) >= 2) args[2] else "centile_grid_refit.csv"

# ---- settings (as reported in the paper) -------------------------------------
centile_levels <- c(0.03, 0.10, 0.25, 0.50, 0.75, 0.90, 0.97)
centile_labels <- c("P3", "P10", "P25", "P50", "P75", "P90", "P97")
families       <- c(NO = "NO", GA = "GA", LN = "LOGNO", WEI = "WEI", BCCG = "BCCG", BCT = "BCT", BCPE = "BCPE")
family_parameters <- list(NO = c("mu", "sigma"), GA = c("mu", "sigma"), LOGNO = c("mu", "sigma"), WEI = c("mu", "sigma"),
                          BCCG = c("mu", "sigma", "nu"), BCT = c("mu", "sigma", "nu", "tau"), BCPE = c("mu", "sigma", "nu", "tau"))
age_power      <- 0.5          # the splines are functions of age^0.5
knots          <- 8            # spline intervals, chosen by athlete-level cross-validation
selection_k    <- "log n"      # Schwarz criterion
nu_df_grid     <- 1:5          # total df for the skewness: 1 = constant, 2 = linear, 3-5 = spline
search_cycles  <- eval(formals(gamlss.control)$n.cyc)
refit_cycles   <- 10 * search_cycles

penalty_value <- function(k, n) if (identical(k, "log n")) log(n) else k
nu_formula <- function(nu_df) {
  if (nu_df == 1) ~ 1 else if (nu_df == 2) ~ t_age else as.formula(paste0("~ pb(t_age, df = ", nu_df - 2, ")"))
}
smooth_term <- function(n, knots, lambda = NULL) {
  if (is.null(lambda) || !is.finite(lambda)) {
    sprintf("pb(t_age, control = pb.control(inter = %d, method = 'GAIC', k = %.6f))", knots, penalty_value(selection_k, n))
  } else sprintf("pb(t_age, lambda = %.8g, control = pb.control(inter = %d))", lambda, knots)
}
fitted_lambdas <- function(m) {
  one <- function(part) tryCatch(m[[part]][[1]]$lambda, error = \(e) NULL)
  list(mu = one("mu.coefSmo"), sigma = one("sigma.coefSmo"))
}

# Fit one family; NULL if it fails, does not converge, or gives non-finite residuals
fit_family <- function(d, family, nu_df = 1, lambdas = NULL, n_cyc = search_cycles) {
  a <- list(formula = as.formula(paste("y ~", smooth_term(nrow(d), knots, lambdas$mu))),
            sigma.formula = as.formula(paste("~", smooth_term(nrow(d), knots, lambdas$sigma))),
            family = family, data = select(d, y, t_age), control = gamlss.control(n.cyc = n_cyc, trace = FALSE))
  if ("nu"  %in% family_parameters[[family]]) a$nu.formula  <- nu_formula(nu_df)
  if ("tau" %in% family_parameters[[family]]) a$tau.formula <- ~ 1
  m <- tryCatch(suppressWarnings(do.call(gamlss, a)), error = \(e) NULL)
  if (is.null(m) || !isTRUE(m$converged)) return(NULL)
  if (!all(is.finite(tryCatch(resid(m), error = \(e) Inf)))) return(NULL)
  m
}

# All candidates: the smoothing of the median and spread is selected once, on a simple model, and then held fixed
fit_candidates <- function(d) {
  base <- NULL
  for (f in c("NO", "LOGNO", "GA")) { base <- fit_family(d, f, n_cyc = refit_cycles); if (!is.null(base)) break }
  lambdas <- if (is.null(base)) NULL else fitted_lambdas(base)
  bind_rows(tibble(family = names(families)[!names(families) %in% c("BCCG", "BCT", "BCPE")], nu_df = NA_integer_),
            expand_grid(family = c("BCCG", "BCT", "BCPE"), nu_df = nu_df_grid)) |>
    mutate(model = map2(family, nu_df, \(f, k) fit_family(d, families[[f]], nu_df = coalesce(k, 1L), lambdas = lambdas))) |>
    filter(!map_lgl(model, is.null)) |>
    mutate(deviance = map_dbl(model, "G.deviance"), df = map_dbl(model, "df.fit"))
}

# Distribution parameters at chosen ages, read from the fitted curves (interpolated between the observed ages)
centiles_at <- function(m, d, ages) {
  pars <- map(set_names(m$parameters), \(p) approx(d$t_age, fitted(m, p), xout = ages^age_power, rule = 2, ties = mean)$y)
  map(centile_levels, \(p) do.call(get(paste0("q", m$family[1])), c(list(p = p), pars))) |>
    set_names(centile_labels) |> as_tibble() |> mutate(age = ages, .before = 1)
}
age_grid <- function(age) seq(ceiling(min(age) * 2) / 2, floor(max(age) * 2) / 2, by = 0.5)

# ---- fit per sex --------------------------------------------------------------
tests <- read_csv(input, show_col_types = FALSE)
y_col <- intersect(c("jump_height_cm", "jump_mean_cm"), names(tests))[1]   # the release has the trial mean per test
tests <- tests |> transmute(sex, age = age_years, y = .data[[y_col]], athlete = if ("athlete" %in% names(tests)) athlete else NA) |>
  filter(!is.na(y), !is.na(age)) |> mutate(t_age = age^age_power)

grids <- map(c("Male", "Female"), \(s) {
  d <- tests |> filter(sex == s)
  cand <- fit_candidates(d)
  best <- which.min(cand$deviance + penalty_value(selection_k, nrow(d)) * cand$df)
  m <- cand$model[[best]]
  message(s, ": n = ", nrow(d), " tests; chosen ", cand$family[[best]], ", skewness df ", cand$nu_df[[best]])
  centiles_at(m, d, age_grid(d$age)) |>
    mutate(test_type = "CMJ", gender = s, variable = "Jump_Height_Imp-Mom_", n_tests = nrow(d),
           n_athletes = if (all(is.na(d$athlete))) NA else n_distinct(d$athlete), .before = 1)
}) |> bind_rows()
write_csv(grids, output); message("written: ", output)
