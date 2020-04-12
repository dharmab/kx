#!/usr/bin/env python3

import kx.configuration.cluster
import kx.utility


def skeletal_fcc() -> dict:
    return {"variant": "fcos", "version": "1.0.0", "ignition": {}}


def _generate_universal_fcc(
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
) -> dict:
    return kx.utility.merge_complex_dictionaries(
        skeletal_fcc(),
        {
            "passwd": {
                "users": [
                    {
                        "name": "core",
                        "ssh_authorized_keys": cluster_configuration.ssh_keys,
                    }
                ]
            }
        },
    )


def generate_common_etcd_fcc(
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
) -> dict:
    return _generate_universal_fcc(cluster_configuration)
