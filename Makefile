.PHONY: run

run:
	uv run python utils/validate_inputs.py
	uv run python main.py

