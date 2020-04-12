#!/usr/bin/env Python

from __future__ import annotations
import typing
import kx.logging
if typing.TYPE_CHECKING:
    import kx.configuration.cluster


logger = kx.logging.get_logger(__name__)


def validate_configuration(configuration: kx.configuration.cluster.ClusterConfiguration) -> None:
    validators = [validate_provider, validate_ssh_keys]

    for f in validators:
        f(configuration)


def validate_provider(configuration: kx.configuration.cluster.ClusterConfiguration) -> None:
    supported_providers = "Vagrant"
    assert (
        configuration.provider in supported_providers
    ), f"provider must be one of {supported_providers}"


def validate_ssh_keys(configuration: kx.configuration.cluster.ClusterConfiguration) -> None:
    if configuration.provider != "Vagrant":
        assert configuration.ssh_keys, "ssh_keys must be defined"
    assert all(
        isinstance(key, str) for key in configuration.ssh_keys
    ), "ssh_keys must be a list of strings"
