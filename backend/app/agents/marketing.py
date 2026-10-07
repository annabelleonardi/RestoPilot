"""Marketing Agent: content plans, campaigns, and customer targeting.

TODO(MVP): LLM-generate content calendars and targeted offers via llm_client;
track campaign performance once outreach data exists.
"""


def content_plan(store_id: int) -> str:
    return (
        "📣 *Content Plan — this week (Warung Bu Sari)*\n"
        "• Mon: Reels — behind the scenes sambal making\n"
        "• Wed: Promo post — Ayam Geprek bundle (boost a slow seller)\n"
        "• Fri: Story — highlight a 4.6★ customer review\n"
        "Best posting times: 11:00 & 18:00 WIB."
    )


def target_segments(store_id: int) -> list[dict]:
    """Identify catering / office-order / event prospects from sales patterns."""
    raise NotImplementedError("Customer targeting lands in the next milestone.")
