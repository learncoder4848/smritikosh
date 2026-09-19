"""Tests for code-aware lexical tokenization."""

from smritikosh.retrieval.tokenizer import tokenize_code


def test_should_retain_and_split_code_identifiers() -> None:
    tokens = tokenize_code("src/report/UnbilledInterest.py idempotent_handler")

    assert "unbilledinterest" in tokens
    assert {"unbilled", "interest"} <= set(tokens)
    assert "idempotent_handler" in tokens
    assert {"idempotent", "handler"} <= set(tokens)
