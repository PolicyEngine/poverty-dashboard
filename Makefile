.PHONY: install deploy recompute recompute-upgrade dev

install:
	pip install -e .
	cd frontend && npm install

deploy:
	modal deploy modal_app.py

recompute:
	python -m scripts.precompute_baseline

recompute-upgrade:
	python -m scripts.precompute_baseline --upgrade

dev:
	cd frontend && npm run dev
