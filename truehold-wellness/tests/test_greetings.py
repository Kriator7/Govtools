from wellness_agent.greetings import is_creed_request, is_crew_request, is_salutation


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


def test_crew_request_matches_class_photo_phrases():
    for text in (
        "lets see the crew",
        "let's see the crew",
        "Let's see the crew!",
        "show me the crew",
        "meet the crew",
        "the crew",
        "class photo",
    ):
        assert is_crew_request(text), text


def test_crew_request_does_not_steal_orders_or_schedule():
    for text in ("team", "schedule", "order 2x klow", "hi", "what do you sell", ""):
        assert not is_crew_request(text), text


def test_creed_request_matches_house_mission_phrases():
    for text in (
        "why do you care",
        "what do you believe",
        "your mission",
        "vitamin C hostage",
        "oranges",
        "who said that quote",
        "Ralph Waldo Emerson",
        "naturally occurring",
        "the people deserve the truth",
        "empowerment",
        "take control of my life",
        "bone broth",
    ):
        assert is_creed_request(text), text
    for text in ("hi", "order 2x klow", "team", "lets see the crew", ""):
        assert not is_creed_request(text), text
