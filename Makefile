VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

# create virtual environment
.PHONY: venv
venv: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	. $(VENV)/bin/activate && pre-commit install
	. $(VENV)/bin/activate && pre-commit autoupdate
	. $(VENV)/bin/activate && pre-commit run --all-files
