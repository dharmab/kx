#!/usr/bin/env Python

from __future__ import annotations
import kx.log
from kx.configuration import cluster


logger = kx.log.get_logger(__name__)


def validate_configuration(config: cluster.ClusterConfiguration) -> None:
    validators = [
        validate_provider,
        validate_ssh_keys
    ]

    for f in validators:
        f(config)


def validate_provider(config: cluster.ClusterConfiguration) -> None:
    supported_providers = ("Vagrant")
    assert config.provider in supported_providers, f"provider must be one of {supported_providers}"


def validate_ssh_keys(config: cluster.ClusterConfiguration) -> None:
    assert config.ssh_keys, "ssh_keys must be defined"
    assert all(isinstance(key, str) for key in config.ssh_keys), "ssh_keys must be a list of strings"
