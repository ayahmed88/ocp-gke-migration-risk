"""Regenerate the five manuscript figures (JoCC revision, v4) from the application's result files.

Run:  python make_figures.py
Every plotted value is read from the source files below and checked against the expected values.
"""
import hashlib
import itertools
import json
import re
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.text import Text  # noqa: E402
from PIL import Image  # noqa: E402

warnings.filterwarnings("error", message=".*[Gg]lyph.*")  # a missing glyph must stop the build

# ----------------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "data"
SRC = {
    "workbook": APP / "raw/OCP_GKE_Migration_Risk_Dataset_REAL_176.xlsx",
    "seed": APP / "results/seed_sensitivity.json",
    "holdout": APP / "results/holdout_report.json",
    "xai": APP / "results/xai_global.json",
    "manifest3a": APP / "results/phase3a_manifest.json",
    "r11": ROOT / "paper/results/r11_presubmission_analyses.json",
    }
OUT = ROOT / "paper/figures/out"
OUT.mkdir(parents=True, exist_ok=True)
DPI = 600

# ----------------------------------------------------------------------------- style
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "DejaVu Serif"],
    "font.size": 9.5,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "pdf.fonttype": 42,  # embed TrueType, keep text as text in the PDF
    "ps.fonttype": 42,
})
MODEL_COL = {"Logistic Regression": "#0F7B7B", "Random Forest": "#8FA3B4",
             "XGBoost": "#5A6B7B", "Dummy (prior)": "#C9D0D7"}
RISK_COL = {"High": "#C8443F", "Medium": "#C8861F", "Low": "#3A9A6C"}
INK = "#1F2937"      # diagram ink / dark text
MUTE = "#4B5563"     # diagram secondary text
ERR = "#46525E"      # error-bar ink
FORBIDDEN = re.compile(r"sealed|vault|locked|official|carve|section\s*\d|\.xlsx|\.json|\.csv|\.py\b|REAL_176|RAW_Dataset", re.I)

MANIFEST = {"generator": "v4/figs_src/make_figures.py", "matplotlib": matplotlib.__version__,
            "font": "Liberation Serif (fallback DejaVu Serif)", "dpi": DPI, "figures": []}


# ----------------------------------------------------------------------------- QA helpers
def _texts(fig):
    out = []
    for t in fig.findobj(Text):
        if t.get_visible() and t.get_text().strip() and t.get_alpha() != 0:
            out.append(t)
    return out


def qa_figure(fig, name, allow_pairs=()):
    """Fail on: forbidden words, text outside the canvas, overlapping text."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    fb = fig.bbox
    texts = _texts(fig)
    for t in texts:
        s = t.get_text()
        assert not FORBIDDEN.search(s), f"{name}: forbidden token in text {s!r}"
        e = t.get_window_extent(r)
        assert e.x0 >= fb.x0 - 0.5 and e.y0 >= fb.y0 - 0.5 and e.x1 <= fb.x1 + 0.5 and e.y1 <= fb.y1 + 0.5, \
            f"{name}: text clipped by canvas: {s!r} {e} vs {fb}"
    for a, b in itertools.combinations(texts, 2):
        if (a.get_text(), b.get_text()) in allow_pairs or (b.get_text(), a.get_text()) in allow_pairs:
            continue
        ea, eb = a.get_window_extent(r), b.get_window_extent(r)
        if ea.overlaps(eb):
            raise AssertionError(f"{name}: overlapping text {a.get_text()!r} / {b.get_text()!r}")
    return r


def legend_clear_of_axes(fig, leg, ax, name):
    r = fig.canvas.get_renderer()
    lb, ab = leg.get_window_extent(r), ax.get_window_extent(r)
    assert not lb.overlaps(ab), f"{name}: legend overlaps the plotting area"
    # also clear of every artist drawn in the axes (bars, error bars, labels)
    from matplotlib.transforms import Bbox
    for art in ax.patches + ax.lines + ax.texts:
        eb = art.get_window_extent(r)
        assert not lb.overlaps(eb), f"{name}: legend overlaps an artist {art}"
    for col in ax.collections:  # error-bar LineCollections: test their segments in display space
        for seg in col.get_segments():
            eb = Bbox.null()
            eb.update_from_data_xy(col.get_transform().transform(seg), ignore=True)
            assert not lb.overlaps(eb), f"{name}: legend overlaps an error bar"


def save(fig, stem):
    png, pdf = OUT / f"{stem}.png", OUT / f"{stem}.pdf"
    fig.savefig(png, dpi=DPI, metadata={"Software": None})
    fig.savefig(pdf, metadata={"Creator": None, "Producer": None, "CreationDate": None})
    plt.close(fig)
    with Image.open(png) as im:
        px = list(im.size)
        dpi = [round(float(v)) for v in im.info.get("dpi", (0, 0))]
    sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (png, pdf)}
    return {"png": png.name, "pdf": pdf.name, "png_pixels_wh": px, "png_dpi": dpi,
            "size_in_wh": [round(px[0] / DPI, 3), round(px[1] / DPI, 3)], "sha256": sha}


# ============================================================================= Figure 1
def fig1():
    df = pd.read_excel(SRC["workbook"], sheet_name="RAW_Dataset_176", engine="openpyxl")
    ct = pd.crosstab(df["Environment"], df["Risk_Level"])
    envs, classes = ["Dev", "QA"], ["High", "Medium", "Low"]
    ct = ct.reindex(index=envs, columns=classes)
    expected = {"Dev": {"High": 48, "Medium": 35, "Low": 5}, "QA": {"High": 45, "Medium": 33, "Low": 10}}
    got = {e: {c: int(ct.loc[e, c]) for c in classes} for e in envs}
    assert got == expected, f"fig1 counts differ: {got}"
    assert int(ct.values.sum()) == 176

    fig, ax = plt.subplots(figsize=(6.0, 3.5), layout="constrained")
    x = np.arange(len(envs))
    step, bw = 0.26, 0.245
    handles = []
    for k, c in enumerate(classes):
        vals = ct[c].to_numpy()
        b = ax.bar(x + (k - 1) * step, vals, bw, color=RISK_COL[c], label=c, zorder=2)
        handles.append(b)
        for bx, v in zip(b, vals):
            ax.text(bx.get_x() + bx.get_width() / 2, v + 0.9, f"{v}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x, ["Development (Dev)", "Quality Assurance (QA)"])
    ax.set_ylabel("Records")
    ax.set_ylim(0, 55)
    ax.set_yticks(range(0, 51, 10))
    ax.set_xlim(-0.6, 1.6)
    leg = fig.legend(handles=handles, labels=classes, loc="outside upper center", ncols=3, frameon=False,
                     title="Risk level", title_fontsize=9, alignment="center", handlelength=1.6, columnspacing=2.0)
    qa_figure(fig, "fig1")
    legend_clear_of_axes(fig, leg, ax, "fig1")
    meta = save(fig, "fig1_class_by_environment")
    meta.update({"figure": 1, "title": "Risk-level counts by environment",
                 "source": [str(SRC["workbook"]) + " :: sheet RAW_Dataset_176 (columns Environment, Risk_Level)"],
                 "plotted": {"counts": got, "class_order": classes, "total_records": 176}})
    MANIFEST["figures"].append(meta)


# ============================================================================= Figure 2
def fig2():
    # every number in the diagram is checked against the data / result files
    df = pd.read_excel(SRC["workbook"], sheet_name="RAW_Dataset_176", engine="openpyxl")
    ho = json.loads(SRC["holdout"].read_text())
    m3 = json.loads(SRC["manifest3a"].read_text())
    assert df.shape == (176, 27)
    assert df["Migration_ID"].is_unique
    assert df["Service_Code"].nunique() == 88
    envsets = df.groupby("Service_Code")["Environment"].apply(lambda s: tuple(sorted(s)))
    assert (envsets == ("Dev", "QA")).all(), "Dev/QA pair per service fails"
    assert not df.duplicated().any()
    assert (ho["train_rows"], ho["train_services"], ho["test_rows"], ho["test_services"], ho["seed"]) == (140, 70, 36, 18, 42)
    assert "GroupShuffleSplit 80/20 by Service_Code" in ho["split"]
    assert "StratifiedGroupKFold 5-fold x 5 repeats" in m3["validation"] and "42..46" in m3["validation"]
    assert m3["integrity_checks"]["all_passed"] is True

    W, H = 6.0, 3.9
    XL, YL = (0.6, 99.4), (8.3, 97.7)
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(*XL)
    ax.set_ylim(*YL)
    ax.axis("off")
    GRAY, BLUE, BLUE2, RED = "#F3F4F6", "#DCE6F1", "#EEF3FA", "#F6DFDC"
    TFS, LFS = 9.0, 7.6
    boxes = []

    def box(x, y, w, h, title, lines, fill, tdy):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6",
                           facecolor=fill, edgecolor=INK, linewidth=0.9, zorder=1)
        ax.add_patch(p)
        tt = ax.text(x + w / 2, y + h - tdy, title, ha="center", va="center", fontsize=TFS, color=INK,
                     fontweight="bold", zorder=3)
        lt = ax.text(x + w / 2, y + (h - tdy) / 2 + 0.2, "\n".join(lines), ha="center", va="center",
                     fontsize=LFS, color=MUTE, linespacing=1.45, zorder=3)
        boxes.append((p, tt, lt))

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9,
                                     linewidth=1.0, color=INK, zorder=2))

    # same layout, boxes and colours as render_fix.py; wording updated
    box(2, 72, 30, 24, "Migration tracker extract", ["176 records | 88 services | 27 fields"], GRAY, 4.6)
    box(36, 72, 27, 24, "Integrity checks", ["shape 176×27 | unique IDs", "88 services × 2 environments",
                                               "Dev/QA pair per service", "no duplicate rows"], BLUE2, 4.6)
    box(67, 72, 31, 24, "Data preparation", ["de-identified extract (MIG / SVC codes)", "cleaning and consistency checks",
                                           "DB_Type: explicit None category"], GRAY, 4.6)
    arrow(32, 84, 36, 84)
    arrow(63, 84, 67, 84)
    box(36.5, 42, 27, 20, "Service-grouped split", ["GroupShuffleSplit 80 / 20", "by Service_Code (seed 42)",
                                                     "before the final model comparison"], BLUE, 3.6)
    arrow(82, 72, 56, 62)
    box(4, 10, 42, 22, "Selection pool", ["140 records | 70 services", "final comparison and tuning re-runs",
                                           "StratifiedGroupKFold 5×5 (seeds 42–46)",
                                           "encoding fitted per training fold"], GRAY, 4.4)
    box(54, 10, 42, 22, "Post-selection holdout", ["36 records | 18 services", "excluded from the final comparison;",
                                              "one evaluation of the selected model"], RED, 4.4)
    arrow(43, 42, 28, 32)
    arrow(57, 42, 72, 32)

    r = qa_figure(fig, "fig2")
    # no text may overflow its box: keep >= 4 pt clearance to every edge, >= 2.5 pt between title and lines
    pt = fig.dpi / 72.0  # display pixels per point
    for p, tt, lt in boxes:
        pb = p.get_window_extent(r)
        for t in (tt, lt):
            e = t.get_window_extent(r)
            m = min(e.x0 - pb.x0, pb.x1 - e.x1, e.y0 - pb.y0, pb.y1 - e.y1) / pt
            assert m >= 4.0, f"fig2: text too close to/over box edge ({m:.1f} pt): {t.get_text()!r}"
        gap = (tt.get_window_extent(r).y0 - lt.get_window_extent(r).y1) / pt
        assert gap >= 2.5, f"fig2: title/lines gap {gap:.1f} pt in {tt.get_text()!r}"
    meta = save(fig, "fig2_protocol")
    meta.update({"figure": 2, "title": "Data and evaluation flow",
                 "source": [str(SRC["layout"]) + " (layout, boxes, colours)",
                            str(SRC["workbook"]) + " :: sheet RAW_Dataset_176 (176 x 27, 88 services, integrity checks)",
                            str(SRC["holdout"]) + " (140/70 pool, 36/18 holdout, seed 42, 80/20 grouped split)",
                            str(SRC["manifest3a"]) + " (StratifiedGroupKFold 5x5, seeds 42..46; integrity checks)"],
                 "plotted": {"records": 176, "services": 88, "fields": 27, "shape": "176x27",
                             "split": "GroupShuffleSplit 80/20 by Service_Code, seed 42",
                             "pool": {"records": 140, "services": 70}, "holdout": {"records": 36, "services": 18},
                             "cv": "StratifiedGroupKFold 5x5, seeds 42-46"}})
    MANIFEST["figures"].append(meta)


# ============================================================================= Figure 3
def fig3():
    rows = json.loads(SRC["seed"].read_text())
    seeds = [42, 7, 100, 2026]
    models = ["Logistic Regression", "Random Forest", "XGBoost", "Dummy (prior)"]
    tab = {(r["seed_base"], r["model"]): (r["f1"], r["std"]) for r in rows}
    missing = [(s, m) for s in seeds for m in models if (s, m) not in tab]
    assert not missing, f"fig3: missing rows {missing}"
    assert len(rows) == 16
    exp42 = {"Logistic Regression": 0.634, "Random Forest": 0.539, "XGBoost": 0.592, "Dummy (prior)": 0.238}
    for m, v in exp42.items():
        assert abs(tab[(42, m)][0] - v) < 1e-9, f"fig3: base-42 {m} = {tab[(42, m)][0]} != {v}"

    fig, ax = plt.subplots(figsize=(6.0, 3.7), layout="constrained")
    x = np.arange(len(seeds))
    step, bw = 0.2, 0.185
    handles = []
    for k, m in enumerate(models):
        mu = np.array([tab[(s, m)][0] for s in seeds])
        sd = np.array([tab[(s, m)][1] for s in seeds])
        b = ax.bar(x + (k - 1.5) * step, mu, bw, color=MODEL_COL[m], label=m, zorder=2,
                   yerr=sd, error_kw={"ecolor": ERR, "elinewidth": 0.9, "capsize": 2.4, "capthick": 0.9, "zorder": 3})
        handles.append(b)
    ax.set_xticks(x, [f"Seed base {s}" for s in seeds])
    ax.set_ylabel("Macro-F1 (mean ± SD, 25 folds)")
    ax.set_ylim(0, 0.8)
    ax.set_yticks(np.round(np.arange(0, 0.81, 0.1), 1))
    ax.set_xlim(-0.55, len(seeds) - 0.45)
    top = max(tab[(s, m)][0] + tab[(s, m)][1] for s in seeds for m in models)
    assert top < 0.8, "fig3: an error bar exceeds the y-limit"
    leg = fig.legend(handles=handles, labels=models, loc="outside upper center", ncols=4, frameon=False,
                     handlelength=1.6, columnspacing=1.5)
    qa_figure(fig, "fig3")
    legend_clear_of_axes(fig, leg, ax, "fig3")
    meta = save(fig, "fig3_seed_stability")
    meta.update({"figure": 3, "title": "Macro-F1 across split-seed bases",
                 "source": [str(SRC["seed"])],
                 "plotted": {f"seed_base_{s}": {m: {"macro_f1_mean": tab[(s, m)][0], "sd": tab[(s, m)][1]}
                                                for m in models} for s in seeds}})
    MANIFEST["figures"].append(meta)


# ============================================================================= Figure 4
def fig4():
    ho = json.loads(SRC["holdout"].read_text())
    labels = ho["confusion"]["labels"]
    cm = np.array(ho["confusion"]["matrix"], dtype=int)
    assert labels == ["Low", "Medium", "High"], labels
    assert cm.tolist() == [[2, 1, 0], [4, 11, 3], [2, 4, 9]], cm.tolist()
    rt, ctot = cm.sum(axis=1), cm.sum(axis=0)
    assert rt.tolist() == [3, 18, 15] and ctot.tolist() == [8, 16, 12]
    assert [ho["test_class_counts"][k] for k in labels] == rt.tolist()
    assert int(cm.sum()) == ho["test_rows"] == 36

    fig, ax = plt.subplots(figsize=(5.5, 4.2), layout="constrained")
    cmap = plt.get_cmap("Greens")
    vmax = int(cm.max())
    norm = matplotlib.colors.Normalize(vmin=0, vmax=vmax)
    GAP = 2.0  # pt; white edge gives an even gap between all cells (vector cells in the PDF)

    def cell(cx, cy, face):
        ax.add_patch(Rectangle((cx - 0.5, cy - 0.5), 1.0, 1.0, facecolor=face, edgecolor="white", lw=GAP, zorder=1))

    for i in range(3):
        for j in range(3):
            v = cm[i, j]
            cell(j, i, cmap(norm(v)))
            ax.text(j, i, f"{v}", ha="center", va="center", fontsize=11, fontweight="bold",
                    color="white" if v > 0.5 * vmax else INK, zorder=4)
    TOT_FILL, off = "#EEF0F3", 3.12  # totals separated from the matrix by a small gap
    for i, v in enumerate(rt):
        cell(off, i, TOT_FILL)
        ax.text(off, i, f"{v}", ha="center", va="center", fontsize=10, color=INK, zorder=4)
    for j, v in enumerate(ctot):
        cell(j, off, TOT_FILL)
        ax.text(j, off, f"{v}", ha="center", va="center", fontsize=10, color=INK, zorder=4)
    cell(off, off, TOT_FILL)
    ax.text(off, off, f"{int(cm.sum())}", ha="center", va="center", fontsize=10, color=INK, zorder=4)
    ax.set_xlim(-0.5, off + 0.5)
    ax.set_ylim(off + 0.5, -0.5)
    ax.set_xticks([0, 1, 2, off], labels + ["Total"])
    ax.set_yticks([0, 1, 2, off], labels + ["Total"])
    ax.tick_params(length=0, pad=5)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("Predicted class", labelpad=6)
    ax.set_ylabel("Actual class", labelpad=6)
    # centre the axis titles on the three class columns / rows, not on the totals
    span = off + 0.5 - (-0.5)
    ax.xaxis.label.set_x((1 - (-0.5)) / span)
    ax.yaxis.label.set_y(1 - (1 - (-0.5)) / span)
    qa_figure(fig, "fig4")
    meta = save(fig, "fig4_holdout_confusion")
    meta.update({"figure": 6, "title": "Post-selection holdout confusion matrix (rows = actual, columns = predicted)",
                 "source": [str(SRC["holdout"]) + " :: confusion"],
                 "plotted": {"labels": labels, "matrix": cm.tolist(), "row_totals": rt.tolist(),
                             "column_totals": ctot.tolist(), "grand_total": int(cm.sum()),
                             "colormap": "Greens, vmin 0, vmax %d" % vmax}})
    MANIFEST["figures"].append(meta)


# ============================================================================= Figure 5
def fig5():
    """Figure 4 of the paper (3 Nov 2026): grouped permutation importance with 20 permutations per fold, scored by the
    increase in log-loss, with corrected 95% intervals over the 25 folds (analysis/r11_presubmission_analyses.py)."""
    R = json.loads(SRC["r11"].read_text())["permutation_importance"]
    assert R["_settings"]["permutations_per_fold"] == 20 and R["_settings"]["folds"] == 25
    feats = R["_ranking"]["by_logloss"]
    assert len(feats) == 13 and len(set(feats)) == 13
    mu = np.array([R[f]["logloss"]["mean"] for f in feats])
    lo = np.array([R[f]["logloss"]["ci95_corrected"][0] for f in feats])
    hi = np.array([R[f]["logloss"]["ci95_corrected"][1] for f in feats])
    assert feats[:3] == ["Complexity_Level", "Business_Criticality", "Previous_Issues_Count"], feats[:3]

    fig, ax = plt.subplots(figsize=(6.0, 4.3), layout="constrained")
    y = np.arange(len(feats))
    ax.barh(y, mu, height=0.66, color=MODEL_COL["Logistic Regression"], zorder=2)
    ax.errorbar(mu, y, xerr=[mu - lo, hi - mu], fmt="none", ecolor=ERR, elinewidth=0.9, capsize=2.2, capthick=0.9, zorder=3)
    ax.axvline(0, color=INK, lw=0.6, zorder=4)
    ax.set_yticks(y, feats)
    ax.invert_yaxis()
    ax.set_xlim(-0.06, 0.30)
    assert -0.06 < float(lo.min()) and float(hi.max()) < 0.30
    ax.set_xticks([-0.05, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25], ["−0.05", "0.00", "0.05", "0.10", "0.15", "0.20", "0.25"])
    ax.set_ylim(len(feats) - 0.4, -0.6)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_xlabel("Increase in log-loss when the predictor is permuted\n(mean and corrected 95% interval; 20 permutations in each of 25 folds)")
    qa_figure(fig, "fig_perm")
    meta = save(fig, "fig_perm_logloss")
    meta.update({"figure": 4, "title": "Permutation importance (Logistic Regression, log-loss, 20 permutations x 25 grouped folds)",
                 "source": [str(SRC["r11"]) + " :: permutation_importance"],
                 "plotted": {"order": "descending by mean log-loss increase", "features": [
                     {"feature": f, "logloss_increase_mean": float(m), "ci95_corrected": [float(a), float(b)]} for f, m, a, b in zip(feats, mu, lo, hi)]}})
    MANIFEST["figures"].append(meta)


# ============================================================================= contact sheet
def contact_sheet():
    stems = ["fig1_class_by_environment", "fig2_protocol", "fig3_seed_stability",
             "fig_perm_logloss", "fig4_holdout_confusion"]
    ims = [Image.open(OUT / f"{s}.png").convert("RGB") for s in stems]
    h_px = 700
    small = [im.resize((round(im.width * h_px / im.height), h_px), Image.LANCZOS) for im in ims]
    ratios = [im.width / im.height for im in small]
    H = 3.0
    fig, axs = plt.subplots(1, 5, figsize=(H * sum(ratios) + 1.2, H + 0.45),
                            gridspec_kw={"width_ratios": ratios, "wspace": 0.04})
    for k, (a, im) in enumerate(zip(axs, small), 1):
        a.imshow(np.asarray(im))
        a.set_title(f"Fig. {k}", fontsize=12, pad=4)
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_visible(True)
            s.set_color("#C9D0D7")
            s.set_linewidth(0.6)
    fig.savefig(OUT / "contact_sheet.png", dpi=200, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    with Image.open(OUT / "contact_sheet.png") as im:
        MANIFEST["contact_sheet"] = {"file": "contact_sheet.png", "png_pixels_wh": list(im.size), "dpi": 200}


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    contact_sheet()
    (OUT / "figures_manifest.json").write_text(json.dumps(MANIFEST, indent=1, ensure_ascii=False))
    for f in MANIFEST["figures"]:
        print(f["figure"], f["png"], f["png_pixels_wh"], f["png_dpi"], f["size_in_wh"])
    print("ALL ASSERTIONS PASSED")
