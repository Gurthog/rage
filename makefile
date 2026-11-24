.PHONY: test check lint run shell


test:
	uv run manage.py test

check:
	uv run manage.py check

lint:
	uv run ruff check .

run:
	uv run manage.py runserver

shell:
	uv run manage.py shell

