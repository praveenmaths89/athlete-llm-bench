.PHONY: install test questions run tables
install:            ## editable install with test dependencies
	python3 -m pip install -e ".[dev]"
test:               ## unit tests (no API key, no network)
	python3 -m pytest -q tests
questions:          ## regenerate the benchmark from data/release (deterministic)
	python3 -I -m lcb.benchmark.generate
run:                ## usage: make run SYSTEM=C MODEL=haiku SPLIT=final  (needs ANTHROPIC_API_KEY in .env)
	python3 -I -m lcb.runner --system $(SYSTEM) --model $(MODEL) --split $(SPLIT) --reps 1
tables:             ## rebuild result tables and figures from the cached runs (no API calls)
	mkdir -p paper/tables paper/figures
	python3 -I -m lcb.analysis.final_tables
	python3 -I -m lcb.analysis.paper_numbers
	python3 -I -m lcb.analysis.result_numbers
	python3 -I -m lcb.analysis.to_latex
	python3 -I -m lcb.analysis.figures
