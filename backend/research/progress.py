"""Research Progress service: YAML checklist + live auto-items -> completion %."""
import yaml
from backend.core import config as C

AUTO = {
 "baseline": lambda: (C.RESULTS_DIR / "phase3a_baseline_results.csv").exists(),
 "winner":   lambda: (C.RESULTS_DIR / "phase4a_winner.json").exists(),
 "xai":      lambda: (C.RESULTS_DIR / "xai_global.json").exists(),
 "rules":    lambda: (C.ROOT / "backend/recommend/rules.yaml").exists(),
 "models":   lambda: (C.ARTIFACTS_DIR / "registry.json").exists(),
 "exports":  lambda: (C.ROOT / "data/exports/manifest.json").exists(),
 "ui":       lambda: (C.ROOT / "frontend/dist/index.html").exists(),
 "docker":   lambda: (C.ROOT / "Dockerfile").exists(),
 "holdout":  lambda: (C.RESULTS_DIR / "holdout_report.json").exists(),
}

def build() -> dict:
    path = C.ROOT / "docs" / "progress.yaml"
    if not path.exists():
        raise FileNotFoundError("docs/progress.yaml is missing from the deployment")
    raw = yaml.safe_load(path.read_text())
    chapters, total_done, total_items = [], 0, 0
    for key, ch in raw.items():
        items = []
        for it in ch["items"]:
            d = it["done"]
            auto = isinstance(d, str) and d.startswith("auto:")
            done = AUTO.get(d.split(":", 1)[1], lambda: False)() if auto else bool(d)
            items.append({"title": it["t"], "done": done, "auto": auto})
        done_n = sum(i["done"] for i in items)
        chapters.append({"id": key, "title": ch["title"], "items": items,
                         "done": done_n, "total": len(items),
                         "pct": round(100 * done_n / len(items))})
        total_done += done_n; total_items += len(items)
    return {"chapters": chapters,
            "overall_pct": round(100 * total_done / total_items),
            "editable_at": "docs/progress.yaml"}
