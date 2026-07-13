-include .env

SOURCE ?= $(DATA_SOURCE)
PYTHON_BIN ?= python

ifeq ($(OS),Windows_NT)
    VENV_PY := .venv/Scripts/python.exe
else
    VENV_PY := .venv/bin/python
endif

.PHONY: setup database ingestion transformation segmentation dashboard all test clean

setup:
	$(PYTHON_BIN) -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements.txt

database:
	$(VENV_PY) -B -m src.database.provision

ingestion:
	$(VENV_PY) -B -m src.ingestion.ingest --source $(SOURCE)

transformation:
	$(VENV_PY) -B -m src.transformation.transform

segmentation:
	$(VENV_PY) -B -m src.segmentation.segment

dashboard:
	$(VENV_PY) -B -m streamlit run src/dashboard/app.py
	
all: database ingestion transformation segmentation

test:
	$(VENV_PY) -B -m pytest -p no:cacheprovider tests/ -v

clean:
	rm -rf .venv .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
