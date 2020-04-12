#!/usr/bin/env python3

import jinja2
import kx.configuration.cluster
import kx.configuration.project
import kx.utility
import yaml


def generate_file(path: str, contents: str, mode: int = 0o644) -> dict:
    return {
        "path": path,
        "contents": {"inline": contents},
        "mode": mode,
        "overwrite": True,
    }


def content_from_file(path: str) -> str:
    file_path = (
        kx.utility.project_directory().joinpath("kx/resources/fcc/files").joinpath(path)
    )
    with open(file_path) as f:
        return f.read()


def content_from_lines(*args) -> str:
    return "\n".join(args)


def template_content(
    content,
    *,
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    project_configuration: kx.configuration.project.ProjectConfiguration,
) -> str:
    return jinja2.Template(content).render(
        cluster_configuration=cluster_configuration,
        project_configuration=project_configuration,
    )


def kubelet_configuration() -> dict:
    # https://kubernetes.io/docs/tasks/administer-cluster/kubelet-config-file/
    return {
        "apiVersion": "kubelet.config.k8s.io/v1beta1",
        "kind": "KubeletConfiguration",
        "kubeletCgroups": "systemd",
        "systemCgroups": "systemd",
        "staticPodPath": "/etc/kubernetes/static_pods/",
        # TODO use webhook mode after bootstrapping TLS PKI
        "authentication": {"anonymous": {"enabled": True}},
        "authorization": {"mode": "AlwaysAllow"},
    }


def skeletal_fcc() -> dict:
    return {
        "variant": "fcos",
        "version": "1.0.0",
        "storage": {
            "files": [
                generate_file(
                    "/etc/selinux/config",
                    content_from_lines("SELINUX=permissive", "SELINUXTYPE=targeted"),
                ),
            ]
        },
        "ignition": {},
    }


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
                    {"path": "/etc/kubernetes/tls"},
                ],
                "files": [
                    generate_file(
                        "/opt/kx/bin/install_kubelet.sh",
                        template_content(
                            content_from_file("scripts/install_kubelet.sh"),
                            cluster_configuration=cluster_configuration,
                            project_configuration=project_configuration,
                        ),
                        mode=0o700,
                    ),
                    generate_file(
                        "/etc/kubernetes/kubelet.yaml",
                        yaml.dump(kubelet_configuration()),
                        mode=0o600,
                    ),
                ],
            },
            "systemd": {
                "units": [
                    {
                        "name": "kubelet.service",
                        "enabled": True,
                        "contents": content_from_file("systemd/kubelet.service"),
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
    return kx.utility.merge_complex_dictionaries(
        _generate_universal_fcc(
            cluster_configuration=cluster_configuration,
            project_configuration=project_configuration,
        ),
        {
            "storage": {
                "files": [
                    generate_file(
                        path="/etc/profile.d/node_role.sh",
                        contents=content_from_lines("NODE_ROLE=etcd"),
                    )
                ]
            }
        },
    )


def generate_common_master_fcc(
    *,
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    project_configuration: kx.configuration.project.ProjectConfiguration,
) -> dict:
    return kx.utility.merge_complex_dictionaries(
        _generate_universal_fcc(
            cluster_configuration=cluster_configuration,
            project_configuration=project_configuration,
        ),
        {
            "storage": {
                "files": [
                    generate_file(
                        path="/etc/profile.d/node_role.sh",
                        contents=content_from_lines("NODE_ROLE=master"),
                    )
                ]
            }
        },
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
