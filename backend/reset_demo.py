"""One-command demo reset for presentations.

Drops and re-seeds the demo database, then replays the demo invoice through
the REAL pipeline (OCR mock -> log_invoice_from_ocr) so the presenter starts
from the exact scripted state: Telur Ayam +16% price spike and one pending
purchase approval on the dashboard work queue.

Usage:  make demo-reset        (from the repo root)
   or:  .venv/bin/python reset_demo.py   (from backend/)

Restart uvicorn after resetting if it was already running.
"""

import os

import app.models  # noqa: F401 — register every model on Base.metadata
from app.agents import procurement
from app.db.seed import ensure_demo_data
from app.db.session import Base, SessionLocal, engine
from app.perception.ocr import MOCK_INVOICE


def main() -> None:
    engine.dispose()
    if os.path.exists("restopilot.db"):
        os.remove("restopilot.db")
    Base.metadata.create_all(engine)
    ensure_demo_data()

    # Replays demo step 1 (owner sends the invoice photo) so the spike draft
    # is already waiting for approval when the presentation starts.
    with SessionLocal() as db:
        result = procurement.log_invoice_from_ocr(db, 1, MOCK_INVOICE, media_url="demo-photo")

    telur = next(a for a in result["audits"] if a["ingredient_name"] == "Telur Ayam")
    print(
        f"✅ Demo DB reset — Warung Bu Sari: 6 ingredients, 14 days of sales, "
        f"6 reviews · Telur Ayam spike +{telur['spike_pct']:.1f}% · "
        f"{len(result['confirmation_ids'])} approval pending on the dashboard. "
        "Restart uvicorn if it was running."
    )


if __name__ == "__main__":
    main()
