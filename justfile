default: lint format_check type_check test

lint:
    uv run ruff check

format_check:
    uv run ruff format --check

type_check:
    uv run pyright

test:
    uv run pytest

watch:
    # Watch for changes and run tests.
    uv run ptw html_tstring/  
