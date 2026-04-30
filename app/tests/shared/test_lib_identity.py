from app.lib.identity import is_email


def test_is_email_returns_true_for_email_string() -> None:
    assert is_email("user@example.com") is True


def test_is_email_returns_false_for_plain_username() -> None:
    assert is_email("john_doe") is False


def test_is_email_returns_true_for_string_with_at_sign() -> None:
    assert is_email("not@@valid") is True


def test_is_email_returns_false_for_empty_string() -> None:
    assert is_email("") is False
