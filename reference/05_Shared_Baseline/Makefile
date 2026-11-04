PYTHON ?= python3
.PHONY: test contracts release-gate product-acceptance manifest-check
test:
	$(PYTHON) -m pytest -q
contracts:
	$(PYTHON) scripts/build_contracts.py
	$(PYTHON) scripts/build_fixtures.py
release-gate:
	$(PYTHON) scripts/release_gate.py
product-acceptance:
	$(PYTHON) scripts/product_acceptance.py
manifest-check:
	$(PYTHON) scripts/verify_manifest.py
