.PHONY: install run test evaluate verify

install:
	python -m pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest -q

evaluate:
	PYTHONPATH=. python scripts/evaluate.py

verify: test evaluate
	python -m compileall -q app
