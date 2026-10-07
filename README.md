# RestoPilot

AI operations copilot for small, owner-run Indonesian restaurants. Two surfaces, one brain:

- **WhatsApp** — the action surface: invoice photos, quick-log purchases (`beli cabai 3 kg 150rb`), stock/price/menu/review reports, and approvals ("ya" / "tidak")
- **Web dashboard** — the monitoring surface: KPIs, inventory, supplier prices, payments, and a "Needs your approval" work queue (HITL confirmations)

## Live prototype

- **Dashboard (static demo):** https://annabelleonardi.github.io/RestoPilot/ — always-on, renders the bundled demo dataset. Approval actions and live WhatsApp chat are staged here (no backend on static hosting) — run locally for the full interactive loop.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 + SQLite. `MOCK_MODE` gates all external integrations (StepFun OCR/LLM, WhatsApp send) — mock and real paths share response shapes.
- **Frontend**: Vite + React 19 + TypeScript + Tailwind CSS, recharts. All agent text is informal Bahasa Indonesia.

## Run it

### Backend (port 8000)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Demo data ("Warung Bu Sari") is seeded automatically on first run.

### Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the dev server proxies `/api` to `localhost:8000`.

## Demo shortcuts (Makefile)

```bash
make demo-reset   # reset the DB to the scripted demo state (spike + pending approval)
make test         # backend pytest suite
make build        # frontend production build
```

## Things to try

- **Dashboard**: approve the pending order in "Needs your approval" — a supplier payment appears in the cash-flow view.
- **WhatsApp demo chat**: step through the full scripted story — invoice photo → price-spike audit → "ya" approval, then a typed quick-log purchase and a voice note (English captions throughout). Or flip on **live mode** and try:
  - `beli cabai 3 kg 150rb` → quick-log purchase, per-kg price reply, +13.6% spike opens a draft order
  - `ya` → approves it; the PO lands in the payments list
  - `beli beras` → the agent asks for the missing price instead of guessing
  - the 🎤 button → sends a voice note (transcription mocked in demo mode)
  - `stok` / `harga supplier` / `menu` / `ulasan` / `konten plan` → real store-scoped reports
- **Invoice photo**: send the demo receipt image — OCR parse, price audit vs 30-day baseline, stock + price history updates.

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q
```
