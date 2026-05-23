import pytest

from app.services.template_engine import (
    eval_derive_expr,
    expand_template,
    validate_template_params,
)


# ---------------------------------------------------------------------------
# expand_template
# ---------------------------------------------------------------------------

def test_expand_two_vary_params():
    params = {
        "lr": {"role": "vary", "values": [1e-3, 1e-4]},
        "batch_size": {"role": "vary", "values": [32, 64]},
    }
    combos = expand_template(params)
    assert len(combos) == 4
    lrs = [c["params"]["lr"] for c in combos]
    bs = [c["params"]["batch_size"] for c in combos]
    assert sorted(set(lrs)) == sorted({1e-3, 1e-4})
    assert sorted(set(bs)) == sorted({32, 64})
    assert [c["combo_index"] for c in combos] == [0, 1, 2, 3]


def test_expand_with_derive():
    params = {
        "d_model": {"role": "vary", "values": [256, 512]},
        "n_heads": {"role": "derive", "expr": "d_model / 64", "from": "d_model"},
    }
    combos = expand_template(params)
    assert len(combos) == 2
    by_dmodel = {c["params"]["d_model"]: c["params"]["n_heads"] for c in combos}
    assert by_dmodel[256] == pytest.approx(4.0)
    assert by_dmodel[512] == pytest.approx(8.0)


def test_expand_fixed_unchanged():
    params = {
        "lr": {"role": "vary", "values": [1e-3, 1e-4, 1e-5]},
        "normalization": {"role": "fixed", "value": "rmsnorm"},
    }
    combos = expand_template(params)
    assert len(combos) == 3
    assert all(c["params"]["normalization"] == "rmsnorm" for c in combos)


# ---------------------------------------------------------------------------
# eval_derive_expr
# ---------------------------------------------------------------------------

def test_eval_divide():
    result = eval_derive_expr("d_model / 64", "d_model", {"d_model": 256})
    assert result == pytest.approx(4.0)


def test_eval_multiply():
    result = eval_derive_expr("d_model * 2", "d_model", {"d_model": 128})
    assert result == pytest.approx(256.0)


def test_eval_add():
    result = eval_derive_expr("n_layers + 2", "n_layers", {"n_layers": 6})
    assert result == pytest.approx(8.0)


def test_eval_floor_div():
    result = eval_derive_expr("d_model // 64", "d_model", {"d_model": 256})
    assert result == 4


def test_eval_conditional_true_branch():
    result = eval_derive_expr(
        "d_model <= 256 → 16, else 8", "d_model", {"d_model": 256}
    )
    assert result == 16


def test_eval_conditional_false_branch():
    result = eval_derive_expr(
        "d_model <= 256 → 16, else 8", "d_model", {"d_model": 512}
    )
    assert result == 8


def test_eval_rejects_unsafe_expr():
    with pytest.raises(ValueError):
        eval_derive_expr("__import__('os')", "d_model", {"d_model": 4})


def test_eval_rejects_power_operator():
    with pytest.raises(ValueError):
        eval_derive_expr("d_model ** 2", "d_model", {"d_model": 4})


def test_eval_rejects_missing_from_param():
    with pytest.raises(ValueError, match="unknown param"):
        eval_derive_expr("x / 2", "x", {})


# ---------------------------------------------------------------------------
# validate_template_params
# ---------------------------------------------------------------------------

def test_validate_valid_params():
    params = {
        "lr": {"role": "vary", "values": [1e-3, 1e-4]},
        "norm": {"role": "fixed", "value": "rmsnorm"},
    }
    errors = validate_template_params(params)
    assert errors == []


def test_validate_no_vary_params():
    params = {
        "norm": {"role": "fixed", "value": "rmsnorm"},
    }
    errors = validate_template_params(params)
    assert any("vary" in e for e in errors)


def test_validate_derive_missing_from_param():
    params = {
        "lr": {"role": "vary", "values": [1e-3]},
        "n_heads": {"role": "derive", "expr": "d_model / 64", "from": "d_model"},
    }
    errors = validate_template_params(params)
    assert any("d_model" in e for e in errors)


def test_validate_circular_derive():
    params = {
        "lr": {"role": "vary", "values": [1e-3]},
        "a": {"role": "derive", "expr": "b * 2", "from": "b"},
        "b": {"role": "derive", "expr": "a * 2", "from": "a"},
    }
    errors = validate_template_params(params)
    assert any("ircular" in e for e in errors)
