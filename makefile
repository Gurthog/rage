.PHONY: check run shell

check:
	uv run manage.py check

run:
	uv run manage.py runserver

shell:
	uv run manage.py shell

