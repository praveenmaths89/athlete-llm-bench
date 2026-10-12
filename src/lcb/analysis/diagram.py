"""End-to-end pipeline diagram (Figure 1). One layout spec writes (1) a draw.io file that can be edited in diagrams.net and
(2) a matplotlib preview used to check the layout. Output: paper/figures/fig_pipeline.drawio and fig_pipeline_preview.png"""
import html
from lcb.config import ROOT

W, H = 900, 400
HDR = {"data": "#2F5D8A", "bench": "#1F8A7A", "sys": "#D9822B", "score": "#7A5C9E", "ana": "#5F6B76"}
TINT = {"data": "#E3ECF6", "bench": "#DDF1EE", "sys": "#FBEBD7", "score": "#ECE6F4", "ana": "#E9ECEF"}
SYS = {"A": ("#F0F0F0", "#7f7f7f"), "C": ("#E1EEF9", "#1f77b4"), "D": ("#FDF0D2", "#E69F00"), "E": ("#E0F2E3", "#2ca02c")}
XS = [0, 185, 370, 555, 740]; CW = 160
cols = [("data", "1  Data and models"), ("bench", "2  Benchmark"), ("sys", "3  Systems"), ("score", "4  Scoring"), ("ana", "5  Analysis")]

boxes = []   # (x, y, w, h, text, fill, stroke, bold, size, font colour); sizes in px (96 px = 1 in)
FS = 11
for (k, title), x in zip(cols, XS): boxes.append((x, 0, CW, 32, title, HDR[k], HDR[k], True, 13, "#FFFFFF"))
def add(c, y, h, text, fill=None, stroke=None, bold=False): boxes.append((XS[c], y, CW, h, text, fill or TINT[cols[c][0]], stroke or HDR[cols[c][0]], bold, FS, "#1a1a1a"))
def sysbox(key, y, h, text): boxes.append((XS[2], y, CW, h, text, SYS[key][0], SYS[key][1], False, FS, "#1a1a1a"))
add(0, 46, 108, "VALD ForceDecks tests\nfootball jumps (CMJ):\n408 tests, 264 athletes,\n1,050 trials,\nde-identified")
add(0, 166, 108, "Centile model (GAMLSS)\nBox\u2013Cox t; median and\nspread smooth in age,\nfitted to 767 jump tests\n\u2192 centile grid P3 \u2026 P97")
add(0, 286, 108, "Measurement noise\nfrom the spread between\ntrials of a test:\nreliable change 3.6 cm\n(men), 5.4 cm (women)")
add(1, 46, 108, "119 questions in five\nfamilies: lookup,\ncentile, longitudinal\n(with cohort), noise,\nedge cases")
add(1, 166, 108, "Reference answers\ncomputed by program\nfrom the tables, the\ngrid and the noise rule;\nno model as judge")
add(1, 286, 108, "Split by athlete\ndevelopment 20\nselection 29\nfinal 70")
boxes.append((XS[2] - 7, 40, CW + 14, 278, "", "#FFFBF4", HDR["sys"], False, FS, "#1a1a1a"))
sysbox("A", 48, 62, "A / A+  single call\nwhole table in the prompt\n(A+: plus noise rule)")
sysbox("C", 118, 50, "B  one agent, \u2264 8 turns\nsql \u00b7 centile \u00b7 tracking")
sysbox("D", 178, 62, "C  coordinator with a\ndata agent and a\nstatistics agent")
sysbox("E", 250, 62, "D  fixed code builds an\nevidence bundle, then\none model call")
add(2, 330, 64, "on Claude Haiku 5.5,\nSonnet 5.5, Opus 5.5", "#FFFFFF", HDR["sys"], True)
add(3, 46, 88, "Compare JSON answer\nwith reference answer:\nevery field must match;\nabstaining counts")
add(3, 146, 36, "Correct", "#DDF1E0", "#2ca02c", True)
add(3, 190, 36, "Wrong answer", "#F9DEDC", "#C0392B", True)
add(3, 234, 50, "No valid answer\n(run stopped at a cap)", "#FFF1CC", "#D9A400", True)
add(3, 296, 98, "Logged per run:\ncost, latency, turns,\ntool calls, responses")
add(4, 46, 88, "Accuracy by system\nand model: strict and\nwith caps raised")
add(4, 146, 72, "Cost and latency\nper question")
add(4, 230, 82, "Output-cap sweep:\nsingle call, cohort-\nlevel questions")
add(4, 324, 70, "Bootstrap intervals\nover athletes; paired\ndifferences")
arrows = [(XS[0] + CW, 200, XS[1], 200), (XS[1] + CW, 200, XS[2] - 7, 200), (XS[2] + CW + 7, 200, XS[3], 200), (XS[3] + CW, 200, XS[4], 200)]


def drawio():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for i, (x, y, w, h, t, fill, stroke, bold, size, fc) in enumerate(boxes):
        style = f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontColor={fc};fontSize={size};fontFamily=Times New Roman;{'fontStyle=1;' if bold else ''}align=center;verticalAlign=middle;"
        cells.append(f'<mxCell id="b{i}" value="{html.escape(t).replace(chr(10), "&lt;br&gt;")}" style="{style}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    for j, (x1, y1, x2, y2) in enumerate(arrows):
        cells.append(f'<mxCell id="a{j}" style="endArrow=block;endFill=1;html=1;strokeColor=#555555;strokeWidth=1.5;" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/><mxPoint x="{x2}" y="{y2}" as="targetPoint"/></mxGeometry></mxCell>')
    xml = f'<mxfile host="app.diagrams.net"><diagram name="Pipeline" id="pipeline"><mxGraphModel dx="900" dy="400" grid="1" gridSize="10" page="1" pageScale="1" pageWidth="900" pageHeight="400"><root>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>'
    (ROOT / "paper/figures/fig_pipeline.drawio").write_text(xml)


def preview():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(W / 96, H / 96)); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    for (x, y, w, h, t, fill, stroke, bold, size, fc) in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=8", fc=fill, ec=stroke, lw=1.5))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=size * 0.75, color=fc, fontweight="bold" if bold else "normal", family="STIXGeneral", linespacing=1.25)
    for (x1, y1, x2, y2) in arrows: ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.4))
    fig.savefig(ROOT / "paper/figures/fig_pipeline_preview.png", dpi=130, bbox_inches="tight"); fig.savefig(ROOT / "paper/figures/fig_pipeline.pdf", bbox_inches="tight")


if __name__ == "__main__":
    drawio(); preview(); print("written")
