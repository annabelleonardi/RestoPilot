"""Marketing agent: store-scoped content plan (mock + LLM paths), safe stubs."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.agents import marketing
from app.db.session import SessionLocal
from app.main import app
from app.models import Store


@pytest.fixture()
def client():
    # Context manager runs the lifespan: creates tables and seeds demo data.
    with TestClient(app) as c:
        yield c


def _make_store(name: str) -> int:
    with SessionLocal() as db:
        store = Store(name=name)
        db.add(store)
        db.commit()
        return store.id


def test_content_plan_mock_is_store_scoped(client) -> None:
    store_id = _make_store("Warung Kopi Senja")
    plan = marketing.content_plan(store_id)
    assert "Warung Kopi Senja" in plan
    assert "Warung Bu Sari" not in plan  # no other tenant's name leaks in
    assert "11:00 & 18:00 WIB" in plan


def test_content_plan_llm_path_uses_llm_text(client) -> None:
    store_id = _make_store("Kedai Makcik")
    with patch("app.agents.marketing.llm_client.generate_content_plan") as gen:
        gen.return_value = (
            "• Sen: Reels — proses bikin kopi\n"
            "• Rab: Post — menu andalan\n"
            "• Jum: Story — ulasan pelanggan"
        )
        plan = marketing.content_plan(store_id)
    gen.assert_called_once_with("Kedai Makcik")
    assert "Kedai Makcik" in plan
    assert "proses bikin kopi" in plan


def test_target_segments_is_safe_stub() -> None:
    assert marketing.target_segments(1) == []


def test_simulate_routes_konten_plan_to_marketing(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "text", "text": "konten plan"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "marketing"
    assert "Warung Bu Sari" in body["reply_text"]  # the seeded demo tenant


def test_simulate_stok_still_procurement(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "text", "text": "stok"}
    )
    assert res.status_code == 200
    assert res.json()["agent"] == "procurement"
