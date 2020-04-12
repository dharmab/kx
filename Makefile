.PHONY: default prepare-provider clean-provider

PYTHON_COMMAND=python -m kx

default:
		@echo 🏴‍☠️

install-tooling:
		$(PYTHON_COMMAND) install-tooling

prepare-provider:
		$(PYTHON_COMMAND) prepare-provider

launch-cluster:
		$(PYTHON_COMMAND) launch-cluster

delete-cluster:
		$(PYTHON_COMMAND) delete-cluster

clean-provider:
		$(PYTHON_COMMAND) clean-provider

uninstall-tooling:
		$(PYTHON_COMMAND) uninstall-tooling
