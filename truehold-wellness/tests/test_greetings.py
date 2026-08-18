from wellness_agent.greetings import is_salutation


def test_salutations_match():
    for text in (
        "hi",
        "Hi!",
        "hello",
        "HELLO",
        "hey there",
        "good morning",
        "Good afternoon.",
        "what's up",
        "hola",
        "👋",
    ):
        assert is_salutation(text), text


def test_non_salutations_do_not_match():
    for text in ("high", "this", "shipping", "order 2x klow", "what do you sell", ""):
        assert not is_salutation(text), text
