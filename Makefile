.PHONY: default prepare-provider clean-provider

KX=python -m kx
PACKAGE=kx

default:
		@echo 🏴‍☠️

install-tooling:
	$(KX) install-tooling

prepare-provider:
	$(KX) prepare-provider

launch-cluster:
	$(KX) launch-cluster

delete-cluster:
	$(KX) delete-cluster

clean-provider:
	$(KX) clean-provider

uninstall-tooling:
	$(KX) uninstall-tooling

lint: typecheck-python check-python-formatting check-python-style

format-python:
	isort --no-sections --use-parentheses --apply --recursive $(PACKAGE)
	black $(PACKAGE)

check-python-formatting:
	black --check $(PACKAGE)

check-python-style:
	pycodestyle --ignore=E501 kx

typecheck-python:
	mypy -p $(PACKAGE)
