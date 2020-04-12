.PHONY: default prepare-provider clean-provider

KX=python -m kx
PACKAGE=kx

default:
		@echo 🏴‍☠️

install-tooling:
	$(KX) install-tooling

prepare-provider:
	$(KX) prepare-provider

create-cluster:
	$(KX) create-cluster

delete-cluster:
	$(KX) delete-cluster

clean-provider:
	$(KX) clean-provider

uninstall-tooling:
	$(KX) uninstall-tooling

lint: check-python-typing check-python-formatting check-python-style

format-python:
	isort --no-sections --use-parentheses --apply --recursive $(PACKAGE)
	black $(PACKAGE)

check-python-formatting:
	black --check $(PACKAGE)

check-python-style:
	pycodestyle --ignore=E501,W503 kx

check-python-typing:
	mypy -p $(PACKAGE)
