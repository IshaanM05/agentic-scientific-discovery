PY ?= python

.PHONY: install calibrate benchmark analyze real demo cli test omnigent-validate all

install:
	$(PY) -m pip install -e ".[demo,dev,real,omnigent]"

calibrate:            ## build likelihood tables from the calibration split only
	$(PY) -m plainsboro.eval.calibrate

benchmark: calibrate  ## matched-condition benchmark on the blind split + figures/report
	$(PY) -m plainsboro.eval.run_benchmark
	$(PY) -m plainsboro.eval.analyze

real:                 ## real Kepler KOI transfer test (downloads ~48 light curves from MAST)
	$(PY) -m plainsboro.data.kepler --per-class 12
	$(PY) -m plainsboro.eval.run_real

demo:
	$(PY) -m streamlit run app/streamlit_app.py

cli:
	$(PY) -m plainsboro.cli investigate T-0167

test:
	$(PY) -m pytest -q

omnigent-validate:
	$(PY) -c "from pathlib import Path; from omnigent.spec.parser import parse; from omnigent.spec.validator import validate; print(validate(parse(Path('omnigent/princeton_plainsboro'), expand_env=False)))"

all: benchmark test
