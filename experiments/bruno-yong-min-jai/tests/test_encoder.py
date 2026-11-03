from backend.encoding.encoders import CANDIDATES, encode, stimulation_budget, order_code

def test_matched_budget_across_labels_and_candidates():
    budgets = set()
    for c in CANDIDATES:
        for lab in ("YES", "NO"):
            b = stimulation_budget(encode(lab, c))
            budgets.add((b["n_pulses"], b["total_charge_nC"], b["max_current_uA"], tuple(b["channels"])))
    assert len(budgets) == 1, budgets

def test_deterministic():
    for c in CANDIDATES:
        assert encode("YES", c) == encode("YES", c)
        assert encode("YES", c) != encode("NO", c)

def test_order_code_differs_only_in_arrangement():
    y, n = order_code("YES"), order_code("NO")
    assert sorted(p.offset_ms for p in y) == sorted(p.offset_ms for p in n)
    assert sorted(p.channel for p in y) == sorted(p.channel for p in n)

def test_rejects_unknown_label():
    import pytest
    with pytest.raises(ValueError):
        encode("MAYBE", CANDIDATES[0])
