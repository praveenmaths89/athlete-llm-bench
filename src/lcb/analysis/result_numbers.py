"""Write paper/results_numbers.tex: macros for the numbers quoted in the text of the results section (from the cached runs, no typing by hand)."""
import json, collections
import numpy as np, pandas as pd
from lcb.config import ROOT
from lcb.analysis import final_tables as ft


def main():
    df = ft.load(); pq = ft.per_question(df); fin = pq[pq.split == "final"]
    M = {}
    names = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus"}; sysn = {"A": "A", "A+": "Ap", "C": "C", "D": "D", "E": "E"}
    for m in ("haiku", "sonnet", "opus"):
        for s in ft.SYS_ORDER:
            d = fin[(fin.model == m) & (fin.system == s)]
            if d.empty: continue
            k = names[m] + sysn[s]
            M["acc" + k] = f"{100*d.ok.mean():.0f}"; M["adj" + k] = f"{100*d.ok_adj.mean():.0f}"; M["noans" + k] = f"{100*d.no_answer.mean():.1f}"
            M["cost" + k] = f"{d.cost.mean():.4f}"; M["turns" + k] = f"{d.turns.mean():.1f}"; M["n" + k] = str(len(d)); M["wrong" + k] = f"{100*(1 - d.ok.mean() - d.no_answer.mean()):.1f}"
            pa = d[~d.cohort]; M["costP" + k] = f"{pa.cost.mean():.4f}"; M["secP" + k] = f"{pa.seconds.mean():.1f}"
            c = d[d.cohort]
            if len(c): M["coh" + k] = f"{100*c.ok.mean():.0f}"; M["cohadj" + k] = f"{100*c.ok_adj.mean():.0f}"; M["ncoh" + k] = str(len(c))
    for m in ("haiku", "sonnet", "opus"):
        n = names[m]
        M["ratioDC" + n] = f"{float(M['cost' + n + 'D']) / float(M['cost' + n + 'C']):.1f}"; M["ratioDE" + n] = f"{float(M['cost' + n + 'D']) / float(M['cost' + n + 'E']):.1f}"
        M["ratioDEP" + n] = f"{float(M['costP' + n + 'D']) / float(M['costP' + n + 'E']):.1f}"; M["ratioCEP" + n] = f"{float(M['costP' + n + 'C']) / float(M['costP' + n + 'E']):.1f}"
        M["latDEP" + n] = f"{float(M['secP' + n + 'D']) / float(M['secP' + n + 'E']):.1f}"; M["latDCP" + n] = f"{float(M['secP' + n + 'D']) / float(M['secP' + n + 'C']):.1f}"
        M["ratioACP" + n] = f"{float(M['costP' + n + 'A']) / float(M['costP' + n + 'C']):.1f}"
        M["ratioCE" + n] = f"{float(M['cost' + n + 'C']) / float(M['cost' + n + 'E']):.1f}"
    # capped runs (all splits) and sensitivity outcome
    caps = collections.Counter(); ok = collections.Counter()
    for l in open(ROOT / "runs_sensitivity/capped_reruns.jsonl"):
        o = json.loads(l); key = {"A": "A", "A+": "Ap", "C": "C"}[o["system"]] + names[o["model"]]; caps[key] += 1; ok[key] += bool(o["score"]["pass"])
    for k in caps: M["capN" + k] = str(caps[k]); M["capOk" + k] = str(ok[k])
    M["capTotal"] = str(sum(caps.values())); M["capOkTotal"] = str(sum(ok.values()))
    allruns = df.groupby(["system", "model"]).size()
    M["runsAHaiku"] = str(int(allruns[("A", "haiku")]))
    # paired differences used in the text (strict, Haiku cohort-level C minus A)
    d = pd.read_csv(ROOT / "results/final_grid/paired_differences.csv")
    r = d[(d.outcome == "strict") & (d.model == "haiku") & (d.comparison == "C minus A") & (d.subset == "cohort_final")].iloc[0]; M["pairedCohortHaiku"] = r.diff_pp.replace("[", "(").replace("]", ")").replace(", ", " to ")
    r = d[(d.outcome == "adjusted") & (d.model == "opus") & (d.comparison == "D minus C") & (d.subset == "final")].iloc[0]; M["pairedDCOpusAdj"] = r.diff_pp.replace("[", "(").replace("]", ")").replace(", ", " to ")
    import re
    for key, (o, m_, cmp_, sub) in {"CohortHaiku": ("strict", "haiku", "C minus A", "cohort_final"), "CohortAdjHaiku": ("adjusted", "haiku", "C minus A", "cohort_final"), "CohortAdjSonnet": ("adjusted", "sonnet", "C minus A", "cohort_final"), "DCOpus": ("adjusted", "opus", "D minus C", "final")}.items():
        r = d[(d.outcome == o) & (d.model == m_) & (d.comparison == cmp_) & (d.subset == sub)].iloc[0]; v, lo, hi = re.findall(r"-?\d+", r.diff_pp)[:3]
        M["gap" + key] = v.lstrip("-") if v.startswith("-") else v; M["gap" + key + "Lo"] = lo; M["gap" + key + "Hi"] = hi; M["gap" + key + "Sign"] = "minus" if v.startswith("-") else "plus"
    cs = pd.read_csv(ROOT / "results/final_grid/capsweep.csv")
    def sw(m, cap, col): return float(cs[(cs.model == m) & (cs.cap == cap)][col].iloc[0])
    M["swHaikuCorrLow"] = f"{100*sw('haiku', 2000, 'correct'):.0f}"; M["swHaikuCorrHigh"] = f"{100*sw('haiku', 16000, 'correct'):.0f}"
    M["swHaikuNoLow"] = f"{100*sw('haiku', 2000, 'no_answer'):.0f}"; M["swHaikuNoMid"] = f"{100*sw('haiku', 4000, 'no_answer'):.0f}"
    M["swSonnetCorrLow"] = f"{100*sw('sonnet', 2000, 'correct'):.0f}"; M["swSonnetCorrMid"] = f"{100*sw('sonnet', 8000, 'correct'):.0f}"; M["swSonnetCorrHigh"] = f"{100*sw('sonnet', 16000, 'correct'):.0f}"
    ha = pd.read_csv(ROOT / "results/final_grid/haiku_all_splits.csv"); M["cohAllHaikuC"] = ha[ha.system == "C"].cohort.iloc[0].split()[0]
    cells = [100 * fin[(fin.model == mm) & (fin.system == ss)].ok_adj.mean() for mm in ("haiku", "sonnet", "opus") for ss in ft.SYS_ORDER if not fin[(fin.model == mm) & (fin.system == ss)].empty]
    M["adjMinAll"] = f"{min(cells):.0f}"; M["adjMaxAll"] = f"{max(cells):.0f}"
    M["gapCohortAdjHaikuAp"] = f"{100 - float(M['cohadjHaikuAp']):.0f}"
    out = "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(M.items())) + "\n"
    (ROOT / "paper/results_numbers.tex").write_text(out); print(out)


if __name__ == "__main__":
    main()
