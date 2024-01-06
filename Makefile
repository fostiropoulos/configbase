
.PHONY: default lint test install

PROJ=configbase

default:
	@echo "No default action, must supply a target"

install:
	pip install -e ."[dev]" -v


lint: black flake8 mypy pylint
	echo "Done"

flake8:
	flake8 ./src/ --count --show-source --statistics
	flake8 --ignore=F841,W503,DOC ./tests/

black:
	black --check --preview .

pylint:
	pylint src

mypy:
	mypy src
