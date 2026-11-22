.PHONY: check run shell test

check:
	uv run manage.py check

run:
	uv run manage.py runserver

shell:
	uv run manage.py shell

test:
	uv run manage.py test

