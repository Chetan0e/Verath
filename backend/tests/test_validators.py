import pytest
from pydantic import ValidationError

from app.core.validators import TextInputValidator, QueryValidator


class TestTextInputValidator:
    def test_accepts_valid_text(self):
        # Regression: this previously raised AttributeError: max_length
        v = TextInputValidator(text="hello world")
        assert v.text == "hello world"

    def test_strips_whitespace(self):
        v = TextInputValidator(text="  spaced  ")
        assert v.text == "spaced"

    def test_enforces_custom_max_length(self):
        with pytest.raises(ValidationError):
            TextInputValidator(text="x" * 30, max_length=5)

    def test_rejects_empty_text(self):
        with pytest.raises(ValidationError):
            TextInputValidator(text="   ")

    @pytest.mark.parametrize("payload", [
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "<img onerror=alert(1)>",
    ])
    def test_rejects_injection_patterns(self, payload):
        with pytest.raises(ValidationError):
            TextInputValidator(text=payload)


class TestQueryValidator:
    def test_accepts_valid_query(self):
        v = QueryValidator(query="find my notes")
        assert v.query == "find my notes"

    def test_enforces_custom_max_length(self):
        with pytest.raises(ValidationError):
            QueryValidator(query="x" * 30, max_length=5)

    def test_rejects_empty_query(self):
        with pytest.raises(ValidationError):
            QueryValidator(query="   ")