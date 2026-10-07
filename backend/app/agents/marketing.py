"""Marketing Agent: weekly content plan (LLM-first, canned fallback), targeting roadmap.

TODO(MVP): track campaign performance once outreach data exists.
"""

from app.db.session import SessionLocal
from app.integrations import llm_client
from app.models import Store


def content_plan(store_id: int) -> str:
    """Weekly content plan — LLM-generated when available, canned fallback otherwise."""
    with SessionLocal() as db:
        store = db.get(Store, store_id)
    store_name = store.name if store else "warung kamu"

    plan = llm_client.generate_content_plan(store_name)
    if plan:
        return (
            f"📣 *Content Plan — this week ({store_name})*\n"
            f"{plan.strip()}\n"
            "Best posting times: 11:00 & 18:00 WIB."
        )
    return (
        f"📣 *Content Plan — this week ({store_name})*\n"
        "• Sen: Reels — keseruan proses masak di dapur\n"
        "• Rab: Post promo — bundle menu best seller\n"
        "• Jum: Story — repost ulasan bintang 5 pelanggan\n"
        "Best posting times: 11:00 & 18:00 WIB."
    )


def target_segments(store_id: int) -> list[dict]:
    """Identify catering / office-order / event prospects from sales patterns.

    Returns [] until outreach data exists — agent functions never raise.
    """
    return []
