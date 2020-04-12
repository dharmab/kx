#!/usr/bin/env python3

import dacite
import dataclasses
import typing
import yaml


@dataclasses.dataclass(frozen=True)
class ClusterConfiguration:
    # Name of the infrastructure provider
    provider: typing.Literal["Vagrant"]
    # List of SSH public keys which will be authorized for the user named "core"
    ssh_keys: typing.List[str]


def load_cluster_configuration(f: typing.IO) -> ClusterConfiguration:
    configuration = dacite.from_dict(
        data_class=ClusterConfiguration, data=yaml.safe_load(f)
    )
    validate_configuration(configuration)
    return configuration


def validate_configuration(configuration: ClusterConfiguration,) -> None:
    validators = [validate_provider, validate_ssh_keys]

    for f in validators:
        f(configuration)


def validate_provider(configuration: ClusterConfiguration,) -> None:
    supported_providers = "Vagrant"
    assert (
        configuration.provider in supported_providers
    ), f"provider must be one of {supported_providers}"


def validate_ssh_keys(configuration: ClusterConfiguration,) -> None:
    if configuration.provider != "Vagrant":
        assert configuration.ssh_keys, "ssh_keys must be defined"
    assert all(
        isinstance(key, str) for key in configuration.ssh_keys
    ), "ssh_keys must be a list of strings"
