from wellness_agent.knowledge.quotes import credited_line, load_quotes, quote_for_host
from wellness_agent.team import member_ids, members


def test_every_host_posts_a_credited_quote():
    quotes = load_quotes()
    assert {row["host"] for row in quotes} == set(member_ids())
    assert len({row["id"] for row in quotes}) == 21
    for row in quotes:
        line = credited_line(row)
        assert row["author"] in line
        assert row["work"] in line
        assert "—" in line
        assert "http" not in line
        assert str(row.get("source") or "").startswith("http")
    for member in members():
        quote = quote_for_host(member["id"])
        assert quote is not None
        assert member["creed"] == credited_line(quote)
        assert quote["author"] in member["creed"]
