#!/usr/bin/env python3
#
# This package contains modules related to loading, validating and accessing
# project configuration.

import dacite
import dataclasses
import typing
import yaml


@dataclasses.dataclass(frozen=True)
class ClusterConfiguration:
    "Struct that contains user-configurable settings"
    # Name of the infrastructure provider
    provider: typing.Literal["Vagrant"]
    # Version of Fedora CoreOS
    operating_system_version = "31.20200323.3.2"
    # Version of Kubernetes
    kubernetes_version = "1.18.1"
    # List of SSH public keys which will be authorized for the user named "core"
    ssh_keys: typing.List[str]
    # Password used to encrypt the cluster's TLS PKI keys at rest
    cluster_tls_pki_encryption_key: str


def load_cluster_configuration(f: typing.IO) -> ClusterConfiguration:
    """
    Load the given configuration YAML or JSON file. The configuration will be
    validated during loading. If the configurable is valid, return a
    configuration struct. Otherwise, raises an exception.

    This should only be called once, in main().
    """
    configuration = dacite.from_dict(
        data_class=ClusterConfiguration, data=yaml.safe_load(f)
    )
    validate_configuration(configuration)
    return configuration


def validate_configuration(configuration: ClusterConfiguration,) -> None:
    """
    Check if the given configuration struct has any obvious mistakes. If the
    configuration is valid, runs to completion. Otherwise, raises an
    AssertError.
    """
    validators = [
        validate_provider,
        validate_ssh_keys,
        validate_cluster_tls_pki_encryption_key,
    ]

    for f in validators:
        f(configuration)


def validate_provider(configuration: ClusterConfiguration,) -> None:
    supported_providers = "Vagrant"
    assert (
        configuration.provider in supported_providers
    ), f"provider must be one of {supported_providers}"


def validate_ssh_keys(configuration: ClusterConfiguration,) -> None:
    # In Vagrant, a hardcoded Vagrant SSH key is available, so ssh_keys is not
    # mandatory
    if configuration.provider != "Vagrant":
        assert configuration.ssh_keys, "ssh_keys must be defined"

    assert all(
        isinstance(key, str) for key in configuration.ssh_keys
    ), "ssh_keys must be a list of strings"

    # TODO check that every key looks like a public key


def validate_cluster_tls_pki_encryption_key(
    configuration: ClusterConfiguration,
) -> None:
    assert configuration.cluster_tls_pki_encryption_key
    # TODO check if the password is shite
