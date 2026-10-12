"""Small statistics helpers: cluster bootstrap and GEE logistic."""
import numpy as np, pandas as pd
import statsmodels.api as sm


def cluster_bootstrap(df: pd.DataFrame, fn, cluster: str, B: int = 2000, seed: int = 1):
    """95% percentile interval of fn(df) resampling whole clusters."""
    rng = np.random.default_rng(seed); groups = [g for _, g in df.groupby(cluster)]; vals = []
    for _ in range(B):
        idx = rng.integers(0, len(groups), len(groups)); vals.append(fn(pd.concat([groups[i] for i in idx])))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def gee_logit(df: pd.DataFrame, y: str, xs: list[str], cluster: str):
    X = sm.add_constant(df[xs].astype(float)); return sm.GEE(df[y].astype(int), X, groups=df[cluster], family=sm.families.Binomial()).fit()
