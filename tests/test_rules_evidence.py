"""Guard: every evidence figure quoted in rules.yaml must match the data.

Born from an external review catch (2026-10-15): R6's headline agreement
carried a denominator slip (91/97 -> 93.8% instead of 91/102 -> 89.2%),
while its own strata (56/56 at >=4, 35/46 at exactly 3) were correct.
This test recomputes every rule's historical agreement from the official
pipeline output and pins it BOTH ways: the recount must equal the expected
figures, and the yaml evidence string must quote those same figures.
Evidence lines can never silently drift from the data again.
"""
import pytest

from backend.core import config as C

pytestmark = pytest.mark.skipif(C.IS_SYNTHETIC_DATA, reason="historical-evidence figures exist only for the real dataset")
from backend.data.pipeline import run as run_pipeline
from backend.recommend.engine import load_rules

PHRASE = {
    "R1": "validate db connectivity",
    "R2": "verify firewall/network rules",
    "R3": "confirm owner availability",
    "R4": "review environment-specific configuration",
    "R5": "review image build pipeline",
    "R6": "test external integrations",
    "R7": "schedule extended validation window",
    "R8": "standard validation and cutover checklist",
}
# (applied, fires) expected from the data — also quoted in rules.yaml
EXPECTED = {
    "R1": (118, 118), "R2": (120, 120), "R3": (46, 46), "R4": (48, 48),
    "R5": (15, 15), "R6": (91, 102), "R7": (68, 93),
}


@pytest.fixture(scope="module")
def frame():
    processed, _groups, _meta = run_pipeline(save=False)
    return processed


def _mask(rid, E):
    if rid == "R1":
        return E.Has_DB_Dependency == 1
    if rid == "R2":
        return (E.Has_Network_Change == 1) | (E.Firewall_Rules_Count >= 5)
    if rid == "R3":
        return E.Owner_Availability.isin(["Delayed", "Unknown"])
    if rid == "R4":
        return (E.Has_Config_Change == 1) & (E.Environment == "QA")
    if rid == "R5":
        return (E.Image_Build_Issue == 1) & (E.Environment == "QA")
    if rid == "R6":
        return E.External_Integrations_Count >= 3
    if rid == "R7":
        return E.Risk_Level == "High"
    raise KeyError(rid)


def test_rules_evidence_matches_data(frame):
    E = frame
    ra = E["Recommended_Action"].fillna("").str.lower()
    rules = {r["id"]: r for r in load_rules()}

    for rid, (k_exp, n_exp) in EXPECTED.items():
        m = _mask(rid, E)
        n = int(m.sum())
        k = int((m & ra.str.contains(PHRASE[rid], regex=False)).sum())
        assert (k, n) == (k_exp, n_exp), f"{rid}: data says {k}/{n}, expected {k_exp}/{n_exp}"
        assert f"{k_exp}/{n_exp}" in rules[rid]["evidence"], \
            f"{rid}: evidence must quote the true figure {k_exp}/{n_exp}"

    # R6 extras: the strata and the corrected headline percentage
    eic = E.External_Integrations_Count
    at3 = eic == 3
    at4 = eic >= 4
    assert (int((at3 & ra.str.contains(PHRASE["R6"], regex=False)).sum()), int(at3.sum())) == (35, 46)
    assert (int((at4 & ra.str.contains(PHRASE["R6"], regex=False)).sum()), int(at4.sum())) == (56, 56)
    ev6 = rules["R6"]["evidence"]
    assert "89.2" in ev6 and "35/46" in ev6 and "56/56" in ev6
    assert all("93.8" not in r["evidence"] for r in rules.values()), \
        "the superseded 93.8% figure must not reappear in any evidence line"

    # R8 fallback: records where no other trigger fires, all carrying the checklist
    others = False
    for rid in EXPECTED:
        if rid != "R7":  # R7 is post-prediction, not a data trigger
            others = others | _mask(rid, E)
    fb = ~others
    assert int(fb.sum()) == 7
    assert bool((ra[fb].str.contains(PHRASE["R8"], regex=False)).all())
    assert "7/7" in rules["R8"]["evidence"]
