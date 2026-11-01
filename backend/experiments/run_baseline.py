"""CLI entry point — delegates to the shared runner (also used by the API)."""
from backend.experiments.runner import run_all


def main():
    def show(e):
        if e["type"] == "model_done":
            print(f"[done] {e['config']:22s} {e['model']:20s} "
                  f"f1_macro={e['f1_macro']:.3f}±{e['f1_macro_std']:.3f} "
                  f"acc={e['accuracy']:.3f} auc={e['auc']:.3f}")
        elif e["type"] == "experiment_finished":
            print("\nSaved:", e["results_path"])
    run_all(progress_cb=show)


if __name__ == "__main__":
    main()
