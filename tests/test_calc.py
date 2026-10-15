import pytest

from learn.calc import CalcError, answer_matches, evaluate, first_number


def test_evaluate_basic():
    assert evaluate("0.5*8*5") == 20
    assert evaluate("1/2 × 12 × 7") == 42
    assert evaluate("sqrt(16) + 2^3") == 12


@pytest.mark.parametrize("expr", ["__import__('os')", "a+1", "(1).real", "open('x')", "2**100", "1/0"])
def test_evaluate_rejects_unsafe_or_invalid(expr):
    with pytest.raises(CalcError):
        evaluate(expr)


def test_answer_matching_allows_stated_rounding():
    assert answer_matches("20 cm²", "0.5*8*5")[0]
    assert answer_matches("3.14", "22/7")[0]
    assert not answer_matches("3.2", "22/7")[0]
    assert not answer_matches("21 cm²", "0.5*8*5")[0]
    assert first_number("1,200 m") == (1200.0, 0)
