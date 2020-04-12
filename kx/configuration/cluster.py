#!/usr/bin/env python3

import typing
import yaml
from kx.configuration import validation
import dacite
import dataclasses


@dataclasses.dataclass(frozen=True)
class ClusterConfiguration():
    # Name of the infrastructure provider
    provider: typing.Literal["Vagrant"]
    # List of SSH public keys which will be authorized for the user named "core"
    ssh_keys: typing.List[str]


def load_cluster_configuration(f: typing.IO) -> ClusterConfiguration:
    configuration = dacite.from_dict(data_class=ClusterConfiguration, data=yaml.safe_load(f))
    validation.validate_configuration(configuration)
    return configuration
