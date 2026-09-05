# All targets run through uv. No script is run outside the uv environment.

install:
	uv sync

# Notebook tooling is a separate dependency group so the pipeline stays lean.
install-notebooks:
	uv sync --group notebooks

# Execute notebooks/plots.ipynb in place so its outputs are embedded. Reads results/ only.
notebook:
	uv run jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/plots.ipynb

smoke:
	uv run python -c "import audit; print(audit.__name__, 'imports')"

gen:
	uv run python scripts/01_generate_transcripts.py --config configs/exp01_generate.yaml

claims:
	uv run python scripts/02_extract_claims.py --config configs/exp02_claims.yaml

score:
	uv run python scripts/03_score_claims.py --config configs/exp03_score.yaml

gap:
	uv run python scripts/03b_reasoning_gap.py --config configs/exp03b_gap.yaml

monitor:
	uv run python scripts/03c_monitor.py --config configs/exp03c_monitor.yaml

verify:
	uv run python scripts/04_verify_claims.py --config configs/exp04_verify.yaml

analyse:
	uv run python scripts/05_analyse.py --config configs/exp05_analyse.yaml

bon:
	uv run python scripts/06_bon.py --config configs/exp06_bon.yaml

# Read-only HTML viewer over results/. Stdlib only, so it needs no uv env.
viewer:
	uv run python viewer/build.py --all

# Results dashboard for the newest stage 05 run.
results:
	uv run python viewer/build.py --results $$(ls -d results/*-05_analyse-* | sort | tail -n 1 | xargs basename)

.PHONY: install install-notebooks notebook smoke gen claims score gap monitor verify analyse bon viewer results
