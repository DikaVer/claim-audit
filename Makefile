# All targets run through uv. No script is run outside the uv environment.

install:
	uv sync

smoke:
	uv run python -c "import audit; print(audit.__name__, 'imports')"

gen:
	uv run python scripts/01_generate_transcripts.py --config configs/exp01_generate.yaml

claims:
	uv run python scripts/02_extract_claims.py --config configs/exp02_claims.yaml

score:
	uv run python scripts/03_score_claims.py --config configs/exp03_score.yaml

verify:
	uv run python scripts/04_verify_claims.py --config configs/exp04_verify.yaml

analyse:
	uv run python scripts/05_analyse.py --config configs/exp05_analyse.yaml

bon:
	uv run python scripts/06_bon.py --config configs/exp06_bon.yaml

# Read-only HTML viewer over results/. Stdlib only, so it needs no uv env.
viewer:
	uv run python viewer/build.py --all

.PHONY: install smoke gen claims score verify analyse bon viewer
