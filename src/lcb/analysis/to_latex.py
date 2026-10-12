"""Turn the result CSVs and the question file into LaTeX tables for the paper (no numbers typed by hand)."""
import json, re, collections
import pandas as pd
from lcb.config import ROOT
from lcb.analysis import final_tables as ft

NAMES = {"haiku": "Haiku 5.5", "sonnet": "Sonnet 5.5", "opus": "Opus 5.5"}
T = ROOT / "paper/tables"


def esc(s): return s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("+", "$+$")


def families():
    qs = [json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl")]
    n = collections.Counter(); 
    for q in qs: n[("Q3c" if q["tags"].get("cohort") else q["family"])] += 1
    rows = [("Q1", "Lookup", "a value, age or trial count", "What was the jump height in test 2?", n["Q1"]),
            ("Q2", "Centile", "the centile band of a test", "Which centile band was the latest test in?", n["Q2"]),
            ("Q3", "Longitudinal", "change, best, mean, span or date over one athlete's tests", "How much did the jump change from first to latest test?", n["Q3"]),
            ("Q3", "Cohort-level", "a count, share or extreme over all athletes", "How many athletes changed beyond measurement noise?", n["Q3c"]),
            ("Q4", "Noise", "whether a change or centile move is real", "Is the change within measurement noise?", n["Q4"]),
            ("Q7", "Edge case", "a missing athlete, test or trial, one test only, or a value outside the reference range", "What was the jump in test 7? (the athlete has three)", n["Q7"])]
    out = ["\\begin{table*}[t]", "\\centering", "\\small", "\\setlength{\\tabcolsep}{5pt}", "\\begin{tabular}{@{}llp{5.6cm}p{5.6cm}r@{}}", "\\toprule", "Family & Name & Asks for & Example & $n$ \\\\", "\\midrule"]
    for r in rows: out.append(f"{r[0]} & {r[1]} & {r[2]} & {r[3]} & {r[4]} \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\caption{Question families. Reference answers are computed by program from the released tables. The numbering follows the repository: Q5 and Q6 are reserved for retrieval and written-explanation questions, which this paper does not include. Appendix~\\ref{app:questions} lists every template.}", "\\label{tab:families}", "\\end{table*}"]
    (T / "families_table.tex").write_text("\n".join(out) + "\n")


def systems():
    rows = [("A\\quad Single call", "tests, trials and centile grid in the prompt (about 42k tokens, cached)", "none", "1"),
            ("A$+$\\quad Single call + rule", "as A, plus the cohort noise rule", "none", "1"),
            ("B\\quad Agent", "the question and the schema", "sql, centile, tracking", "8"),
            ("C\\quad Multi-agent", "coordinator: the question; specialists: data (sql) and statistics (centile, tracking)", "via specialists", "8 + 6"),
            ("D\\quad Fixed pipeline", "the question and an evidence bundle built by code", "none", "1")]
    out = ["\\begin{table*}[t]", "\\centering", "\\small", "\\setlength{\\tabcolsep}{5pt}", "\\begin{tabular}{@{}lp{6.6cm}p{3.4cm}r@{}}", "\\toprule", "System & The model receives & Tools & Turns \\\\", "\\midrule"]
    for r in rows: out.append(f"{r[0]} & {r[1]} & {r[2]} & {r[3]} \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\caption{The five systems. Each runs on one Claude model at a time and returns the same JSON answer. Turns are the maximum number of model calls.}", "\\label{tab:systems}", "\\end{table*}"]
    (T / "systems_table.tex").write_text("\n".join(out) + "\n")


SYSN = {"A": "A\\quad Single call", "A+": "A$+$\\quad Single call + rule", "C": "B\\quad Agent", "D": "C\\quad Multi-agent", "E": "D\\quad Fixed pipeline"}


SYSS = {k: v.replace("\\quad ", " ") for k, v in SYSN.items()}


def results():
    df = ft.load(); pq = ft.per_question(df); fin = pq[pq.split == "final"]; ms = ("haiku", "sonnet", "opus")
    out = ["\\begin{table*}[t]", "\\centering", "\\footnotesize", "\\setlength{\\tabcolsep}{1.9pt}", "\\begin{tabular}{@{}l" + "rrrr" * 3 + "@{}}", "\\toprule",
           "& " + " & ".join(f"\\multicolumn{{4}}{{c}}{{{NAMES[m]}}}" for m in ms) + " \\\\",
           "".join(f"\\cmidrule(lr){{{2 + 4 * k}-{5 + 4 * k}}}" for k in range(3)),
           "System" + " & Corr./NA & Adj. & USD/q & Sec/q" * 3 + " \\\\", "\\midrule"]
    for s in ft.SYS_ORDER:
        cells = []
        for m in ms:
            d = fin[(fin.model == m) & (fin.system == s)]
            cells += ["--"] * 4 if d.empty else [f"{100*d.ok.mean():.0f} / {100*d.no_answer.mean():.0f}", f"{100*d.ok_adj.mean():.0f}", f"{d.cost.mean():.4f}", f"{d.seconds.mean():.1f}"]
        out.append(SYSN[s] + " & " + " & ".join(cells) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\caption{Final split: accuracy, cost and latency of the five systems on three models. Corr. is the percent of questions answered correctly, a missing answer counting as wrong, followed by the percent of runs that ended at a cap without a valid answer (NA, no answer); Adj. is the percent correct after re-running capped runs with larger caps. USD/q and Sec/q are the mean cost and mean wall-clock time per question (runs that hit a cap are included at the time they took). Haiku: 70 questions with three repeats; Sonnet: 70, one run; Opus: 36 (a fixed half), one run. D answers only the per-athlete questions (62, 62 and 32). A$+$ (single call with the noise rule added to the prompt) was run with Haiku only. The letters differ from the repository (Section~\\ref{sec:systems}).}", "\\label{tab:main}", "\\end{table*}"]
    (T / "main_table.tex").write_text("\n".join(out) + "\n")


def family_acc():
    t = pd.read_csv(ROOT / "results/final_grid/accuracy_by_family_final.csv")
    out = ["\\begin{table}[t]", "\\centering", "\\small", "\\setlength{\\tabcolsep}{4pt}", "\\begin{tabular}{@{}lrrrrr@{}}", "\\toprule", "System & Q1 & Q2 & Q3 & Q4 & Q7 \\\\"]
    for m in ("haiku", "sonnet", "opus"):
        out += ["\\midrule", f"\\multicolumn{{6}}{{@{{}}l}}{{\\textit{{{NAMES[m]}}}}} \\\\"]
        for _, r in t[t.model == m].iterrows():
            out.append(f"{SYSS[r.system]} & " + " & ".join(str(r[f]).split()[0] for f in ("Q1", "Q2", "Q3", "Q4", "Q7")) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\caption{Strict accuracy (percent correct, a missing answer counting as wrong) by question family on the final split. Q3 includes the cohort-level questions, which the fixed pipeline does not answer. Family sizes are in Table~\\ref{tab:families}.}", "\\label{tab:family}", "\\end{table}"]
    (T / "family_acc_table.tex").write_text("\n".join(out) + "\n")


def appendix():
    t = pd.read_csv(ROOT / "results/final_grid/accuracy_final_split.csv")
    ap = ["\\begin{table*}[ht]", "\\centering", "\\footnotesize", "\\setlength{\\tabcolsep}{3pt}", "\\begin{tabular}{@{}llrlllr@{}}", "\\toprule", "Model & System & $n$ & Correct [95\\% CI] & Adjusted [95\\% CI] & Cohort-level, adjusted ($n_c$) & USD/q \\\\", "\\midrule"]
    for _, r in t.iterrows():
        coh = "--" if str(r.cohort_acc_adj) in ("n/a", "nan") else f"{r.cohort_acc_adj} ({r.cohort_n})"
        ap.append(f"{NAMES[r.model]} & {SYSS[r.system]} & {r.questions} & {r.accuracy} & {r.accuracy_adjusted} & {coh} & {float(r.cost_per_q):.4f} \\\\")
    ap += ["\\bottomrule", "\\end{tabular}", "\\caption{Final split with 95\\% bootstrap intervals over athletes (the exact one-sided bound $0.025^{1/n}$ when every question is correct). $n_c$: cohort-level questions; USD/q is the mean over all $n$ questions.}", "\\label{tab:ci}", "\\end{table*}"]
    (T / "ci_table.tex").write_text("\n".join(ap).replace("nan", "--") + "\n")
    cs = pd.read_csv(ROOT / "results/final_grid/capsweep.csv")
    sw = ["\\begin{table}[t]", "\\centering", "\\footnotesize", "\\setlength{\\tabcolsep}{4pt}", "\\begin{tabular}{@{}lrrrrr@{}}", "\\toprule", "Model & Cap & Runs & Corr. & No ans. & Out. tok. \\\\", "\\midrule"]
    for _, r in cs.iterrows(): sw.append(f"{NAMES[r.model]} & {int(r.cap):,} & {int(r.runs)} & {100*r.correct:.0f} & {100*r.no_answer:.0f} & {r.mean_out_tokens:,.0f} \\\\".replace(",", "{,}"))
    sw += ["\\bottomrule", "\\end{tabular}", "\\caption{System A on the 12 cohort-level questions at four output caps (percent of runs; Haiku three repeats, Sonnet one; mean output tokens per run).}", "\\label{tab:sweep}", "\\end{table}"]
    (T / "sweep_table.tex").write_text("\n".join(sw) + "\n")
    qs = [json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl")]; by = collections.defaultdict(list)
    for q in qs: by[(q["family"], q["template"])].append(q)
    rows = ["\\begin{table*}[p]", "\\centering", "\\footnotesize", "\\setlength{\\tabcolsep}{3pt}", "\\begin{tabular}{@{}lp{4.3cm}rp{8.0cm}@{}}", "\\toprule", "Fam. & Template & $n$ & Example question \\\\", "\\midrule"]
    for (f, tpl), v in sorted(by.items()):
        ex = re.sub(r"\bA[0-9a-f]{10}\b", "A\\\\ldots", v[0]["text"]).replace("%", "\\%").replace("$", "\\$")
        rows.append(f"{f} & {esc(tpl)} & {len(v)} & {ex} \\\\")
    rows += ["\\bottomrule", "\\end{tabular}", "\\caption{All question templates with one example each (athlete identifiers abbreviated).}", "\\label{tab:templates}", "\\end{table*}"]
    (T / "templates_table.tex").write_text("\n".join(rows) + "\n")


def tex_escape(text: str) -> str:
    out = text.replace("\n", " ")
    for a, b in (("\\", ""), ("_", "\\_"), ("%", "\\%"), ("&", "\\&"), ("#", "\\#"), ("{", "\\{"), ("}", "\\}"), ("<", "\\textless{}"), (">", "\\textgreater{}")):
        out = out.replace(a, b)
    return out


def prompts():
    from lcb.benchmark.schema import ANSWER_INSTRUCTIONS
    from lcb.systems import c_agent, d_multi
    from lcb.systems.prompts import NOISE_RULE
    items = [("Answer instructions (all systems)", ANSWER_INSTRUCTIONS), ("System B", c_agent.SYSTEM), ("System C, coordinator", d_multi.COORD_SYS),
             ("System C, data specialist", d_multi.DATA_SYS), ("System C, statistics specialist", d_multi.STATS_SYS), ("Noise rule (A+ and D)", NOISE_RULE.format(m="3.6", f="5.4"))]
    parts = ["\\paragraph{" + name + ".} {\\footnotesize\\ttfamily\\raggedright " + tex_escape(text if name.startswith("Answer instructions") else text.replace(ANSWER_INSTRUCTIONS, "[answer instructions as above]")) + "\\par}" for name, text in items]
    (T / "prompts.tex").write_text("\n".join(parts) + "\n")


def main():
    T.mkdir(parents=True, exist_ok=True); families(); systems(); results(); family_acc(); appendix(); prompts(); print("tables written")


if __name__ == "__main__":
    main()
