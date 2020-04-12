#!/usr/bin/env python3

import kx.configuration.cluster
import kx.configuration.project
import kx.utility


def content_from_file(path: str) -> str:
    file_path = (
        kx.utility.project_directory().joinpath("kx/resources/fcc/files").joinpath(path)
    )
    with open(file_path) as f:
        return f.read()


def content_from_lines(*args) -> str:
    return "\n".join(args)


def skeletal_fcc() -> dict:
    return {"variant": "fcos", "version": "1.0.0", "ignition": {}}


def _generate_universal_fcc(
    *,
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    project_configuration: kx.configuration.project.ProjectConfiguration,
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
            },
            "storage": {
                "directories": [
                    {"path": "/opt/kx/bin"},
                    {"path": "/opt/kubernetes/bin"},
                ],
                "files": [
                    {
                        "path": "/etc/selinux/config",
                        "contents": {
                            "inline": content_from_lines(
                                "SELINUX=permissive", "SELINUXTYPE=targeted"
                            )
                        },
                        "overwrite": True,
                    },
                    {
                        "path": "/opt/kx/bin/install_kubelet.sh",
                        "contents": {
                            "inline": content_from_file("scripts/install_kubelet.sh")
                        },
                        "mode": 0o755,
                    },
                ],
            },
            "systemd": {
                "units": [
                    {
                        "name": "kubelet.service",
                        "enabled": True,
                        "contents": content_from_file("systemd/kubelet.service"),
                        "dropins": [
                            {
                                "name": "kubernetes-version.conf",
                                "contents": content_from_lines(
                                    "[Service]",
                                    f"Environment=KUBERNETES_VERSION={project_configuration.kubernetes_version}",
                                ),
                            }
                        ],
                    }
                ]
            },
        },
    )


def generate_common_etcd_fcc(
    *,
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    project_configuration: kx.configuration.project.ProjectConfiguration,
) -> dict:
    return _generate_universal_fcc(
        cluster_configuration=cluster_configuration,
        project_configuration=project_configuration,
    )


def generate_common_master_fcc(
    *,
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    project_configuration: kx.configuration.project.ProjectConfiguration,
) -> dict:
    return _generate_universal_fcc(
        cluster_configuration=cluster_configuration,
        project_configuration=project_configuration,
    )


def generate_common_worker_fcc(
    *,
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    project_configuration: kx.configuration.project.ProjectConfiguration,
    pool_name: str,
) -> dict:
    return _generate_universal_fcc(
        cluster_configuration=cluster_configuration,
        project_configuration=project_configuration,
    )
