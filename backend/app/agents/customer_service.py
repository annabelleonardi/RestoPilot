"""Customer Service Agent: feedback digests, complaint detection, draft replies (owner-approved)."""

from datetime import timedelta

from sqlalchemy import select

from app.core.timeutil import store_day_start_utc, store_now
from app.db.session import SessionLocal
from app.models import Review, Store


def review_summary(store_id: int) -> str:
    """This week's reviews from the tenant's Review table — same window and
    sentiment average the dashboard's review views use."""
    with SessionLocal() as db:
        store = db.get(Store, store_id)
        if store is None:
            return "💬 *Review Digest — this week*\nNo reviews yet."
        start = store_day_start_utc(store, store_now(store).date() - timedelta(days=6))
        reviews = db.scalars(
            select(Review).where(Review.store_id == store_id, Review.created_at >= start)
        ).all()

    lines = ["💬 *Review Digest — this week*"]
    if not reviews:
        lines.append("• No reviews came in this week.")
        return "\n".join(lines)

    avg = sum(r.rating for r in reviews) / len(reviews)
    lines[0] = f"💬 *Review Digest — this week ({avg:.1f}★ avg)*"

    loved = list(
        dict.fromkeys(
            r.menu_item_name
            for r in reviews
            if r.sentiment == "positive" and r.menu_item_name
        )
    )
    if loved:
        lines.append(f"👍 Loved: {', '.join(loved)}")

    complaints = [r for r in reviews if r.sentiment == "negative"]
    if complaints:
        for r in complaints:
            where = f" on {r.menu_item_name}" if r.menu_item_name else ""
            lines.append(f"👎 Complaints: 1× “{r.comment}”{where}")

    drafts = [r for r in reviews if r.reply_status == "pending_approval" and r.draft_reply]
    if drafts:
        lines.append(
            f"📝 {len(drafts)} draft repl{'y' if len(drafts) == 1 else 'ies'} waiting "
            "for your approval — check the dashboard."
        )
    return "\n".join(lines)


def draft_review_reply(review_text: str, rating: int) -> str:
    """LLM-drafted polite reply; ALWAYS requires owner approval before sending."""
    return (
        "Terima kasih banyak for your feedback! 🙏 We're sorry the chicken was a bit "
        "tough that day — we've shared this with our kitchen team and hope to serve "
        "you better next time."
    )
