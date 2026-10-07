# RestoPilot — demo & dev shortcuts

demo-reset:
	cd backend && .venv/bin/python reset_demo.py

test:
	cd backend && .venv/bin/python -m pytest -q

build:
	cd frontend && npm run build

.PHONY: demo-reset test build
