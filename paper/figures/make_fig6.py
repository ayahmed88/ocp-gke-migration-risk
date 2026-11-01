"""Figures 6 and 7: decision-support prototype. Fig 6 = architecture drawn from the application's code structure.
Fig 7 = annotated New case prediction screen (screenshot at paper/figures/screens/predict_en.png).
Run:  python make_fig6.py
"""
import hashlib, json, re, warnings
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

warnings.filterwarnings("error", message=".*[Gg]lyph.*")
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "paper/figures/out"; DPI = 600
SCREEN = ROOT / "paper/figures/screens/predict_en.png"
plt.rcParams.update({"font.family": "serif", "font.serif": ["Liberation Serif", "DejaVu Serif"], "font.size": 9.5,
                     "figure.facecolor": "white", "savefig.facecolor": "white", "pdf.fonttype": 42, "ps.fonttype": 42})
INK, MUTE = "#1F2937", "#4B5563"
GRAY, BLUE2, TEAL = "#F3F4F6", "#EEF3FA", "#E3F1F1"
FORBIDDEN = re.compile(r"sealed|vault|locked|official|carve|section\s*\d|\.xlsx|\.json|\.csv|\.py\b|REAL_176|RAW_Dataset", re.I)

# facts checked against the code: backend/api/main.py (28 route decorators), frontend nav (14 pages), i18n en/ar,
# models/registry.py (serving models refit on all 176), explain/explainer.py (exact additive attribution), recommend/rules.yaml (R1-R8)
APP = ROOT
routes = len(re.findall(r"^@app\.(get|post|put|delete)", (APP / "backend/api/main.py").read_text(), re.M))
pages = len(json.loads((APP / "frontend/src/i18n/en.json").read_text())["nav"])
assert routes == 28 and pages == 14, (routes, pages)
assert (APP / "frontend/src/i18n/ar.json").exists()

def draw_arch(ax):
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    TFS, LFS = 8.6, 7.2
    def box(x, y, w, h, title, lines, fill, tdy=4.2):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6",
                                    facecolor=fill, edgecolor=INK, linewidth=0.9, zorder=1))
        ax.text(x + w / 2, y + h - tdy, title, ha="center", va="center", fontsize=TFS, color=INK, fontweight="bold", zorder=3)
        if lines:
            ax.text(x + w / 2, y + (h - tdy) / 2 + 0.3, "\n".join(lines), ha="center", va="center", fontsize=LFS,
                    color=MUTE, linespacing=1.4, zorder=3)
    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, linewidth=1.0, color=INK, zorder=2))
    # interface band
    ax.add_patch(FancyBboxPatch((1, 86), 98, 12, boxstyle="round,pad=0.3,rounding_size=1.2", facecolor="white",
                                edgecolor=INK, linewidth=0.8, linestyle=(0, (3, 2)), zorder=0))
    ax.text(50, 92, f"Web interface (React single-page application, English and Arabic, {pages} pages)  →  "
                    f"REST API (FastAPI, {routes} endpoints)", ha="center", va="center", fontsize=8.0, color=INK)
    # study path (top row)
    box(1, 60, 22, 20, "Data layer", ["de-identified extract", "cleaning with audit log", "integrity checks"], GRAY)
    box(26, 60, 24, 20, "Experimentation", ["service-grouped CV, seed study,", "tuning, holdout evaluation", "run manifests"], GRAY)
    box(53, 60, 22, 20, "Result store", ["result files and", "provenance manifests,", "separate from session state"], BLUE2)
    box(78, 60, 21, 20, "Exports", ["figures and tables", "generated from the", "result files"], BLUE2)
    arrow(23, 70, 26, 70); arrow(50, 70, 53, 70); arrow(75, 70, 78, 70)
    # serving path (bottom row)
    box(1, 20, 22, 26, "New case inputs", ["13 planning-stage", "attributes entered", "by the engineer"], TEAL)
    box(26, 20, 24, 26, "Prediction", ["serving models refit on", "all 176 records (LR primary;", "RF and XGBoost selectable)", "class probabilities"], TEAL)
    box(53, 20, 22, 26, "Explanation", ["exact additive attribution", "per attribute (LR);", "permutation importance"], TEAL)
    box(78, 20, 21, 26, "Rule engine", ["R1 to R8: rule id,", "triggering values,", "priority, stage"], TEAL)
    arrow(23, 33, 26, 33); arrow(50, 33, 53, 33); arrow(75, 33, 78, 33)
    # model registry link from experimentation to prediction
    arrow(38, 60, 38, 46)
    ax.text(39.5, 53, "declared configurations", fontsize=6.9, color=MUTE, va="center")
    # engineer decision
    ax.add_patch(FancyBboxPatch((1, 2), 98, 12, boxstyle="round,pad=0.3,rounding_size=1.2", facecolor="white",
                                edgecolor=INK, linewidth=0.8, zorder=1))
    ax.text(50, 8, "Output reviewed by the migration engineer: predicted level, class probabilities,\n"
                   "attribute contributions and recommended actions with their rules", ha="center", va="center", fontsize=7.4, color=INK, linespacing=1.4)
    arrow(88, 20, 88, 14)
    ax.text(99, 82, "study path", fontsize=7.4, color=MUTE, style="italic", ha="right")
    ax.text(99, 48, "serving path", fontsize=7.4, color=MUTE, style="italic", ha="right")

have_screen = SCREEN.exists()
# ---- Figure 6: architecture
fig = plt.figure(figsize=(5.6, 3.6))
ax1 = fig.add_axes([0.01, 0.01, 0.98, 0.98]); draw_arch(ax1)
for t in fig.findobj(matplotlib.text.Text):
    assert not FORBIDDEN.search(t.get_text() or ""), t.get_text()
png, pdf = OUT / "fig6_prototype.png", OUT / "fig6_prototype.pdf"
fig.savefig(png, dpi=DPI, metadata={"Software": None}); fig.savefig(pdf, metadata={"Creator": None, "Producer": None, "CreationDate": None})
plt.close(fig)
m = json.loads((OUT / "figures_manifest.json").read_text()) if (OUT / "figures_manifest.json").exists() else {}
def _px(path):
    with Image.open(path) as im:
        return list(im.size)
m["fig6_prototype"] = {"generator": "v4/figs_src/make_fig6.py", "facts": {"rest_endpoints": routes, "pages": pages, "languages": ["en", "ar"]},
                       "png_pixels_wh": _px(png), "png_dpi": DPI,
                       "sha256": {q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in (png, pdf)}}
# ---- Figure 7: annotated New case prediction screen (record MIG-006), screenshot supplied by A.Y.A. on 1 Nov 2026
if have_screen:
    im = Image.open(SCREEN).convert("RGB"); W, H = im.size
    fig = plt.figure(figsize=(5.6, 5.6 * H / W))
    ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(im); ax.axis("off")
    CALL = [(1, 660, 205), (2, 1345, 265), (3, 275, 705), (4, 250, 814), (5, 300, 1218), (6, 300, 1464)]
    for n, x, y in CALL:
        ax.add_patch(plt.Circle((x, y), 34, facecolor="#1F2937", edgecolor="white", linewidth=1.6, zorder=5))
        ax.text(x, y, str(n), color="white", fontsize=9.5, fontweight="bold", ha="center", va="center", zorder=6)
    png7, pdf7 = OUT / "fig7_prediction_screen.png", OUT / "fig7_prediction_screen.pdf"
    fig.savefig(png7, dpi=DPI, metadata={"Software": None}); fig.savefig(pdf7, metadata={"Creator": None, "Producer": None, "CreationDate": None})
    plt.close(fig)
    m["fig7_prediction_screen"] = {"generator": "v4/figs_src/make_fig6.py", "png_pixels_wh": _px(png7), "png_dpi": DPI, "source": "screenshot of the v45 application, New case prediction page, record MIG-006, English interface (A.Y.A., 1 Nov 2026); cropped to the content area",
                                   "callouts": {1: "model selection", 2: "13 planning-stage inputs", 3: "Compute risk", 4: "predicted level, risk meter, class probabilities", 5: "attribute contributions", 6: "recommended actions with rule identifiers"},
                                   "values_checked_against_rerun": {"High": 0.972, "Medium": 0.028, "Low": 0.0, "contrib": {"Complexity_Level": 1.53, "Service_Category=Integration": 0.63, "Has_DB_Dependency": 0.52}, "rules": ["R1", "R2", "R7", "R3", "R6"]},
                                   "sha256": {q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in (png7, pdf7)}}
(OUT / "figures_manifest.json").write_text(json.dumps(m, indent=1))
print("fig6 written; fig7 written:", have_screen)
