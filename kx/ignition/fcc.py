#!/usr/bin/env python3

import abc
import jinja2
import kx.configuration
import kx.tls.pki
import kx.utility
import yaml
import yarl


def file_from_content(path: str, contents: str, *, mode: int = 0o644) -> dict:
    return {
        "path": path,
        "contents": {"inline": contents},
        "mode": mode,
        "overwrite": True,
    }


def file_from_url(path: str, url: yarl.URL, *, mode: int = 0o644) -> dict:
    return {
        "path": path,
        "contents": {"source": url.human_repr()},
        "mode": mode,
        "overwrite": True,
    }


def content_from_repository(path: str) -> str:
    file_path = (
        kx.utility.project_directory().joinpath("kx/resources/fcc").joinpath(path)
    )
    with open(file_path) as f:
        return f.read()


def content_from_lines(*args) -> str:
    return "\n".join(args)


def template_content(
    content, *, cluster_configuration: kx.configuration.ClusterConfiguration,
) -> str:
    return jinja2.Template(content).render(cluster_configuration=cluster_configuration,)


class FedoraCoreOSConfigurationProvider(abc.ABC):
    @abc.abstractmethod
    def generate_etcd_configuration(self) -> dict:
        pass

    @abc.abstractmethod
    def generate_master_configuration(self) -> dict:
        pass

    @abc.abstractmethod
    def generate_worker_configuration(self, *, pool_name: str) -> dict:
        pass


class UniversalFCCProvider(FedoraCoreOSConfigurationProvider):
    def __init__(
        self, *, cluster_configuration: kx.configuration.ClusterConfiguration,
    ):
        self.__cluster_configuration = cluster_configuration

    @staticmethod
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

    def __generate_base_configuration(self) -> dict:
        return kx.utility.merge_complex_dictionaries(
            {
                "variant": "fcos",
                "version": "1.0.0",
                "ignition": {},
                "passwd": {
                    "users": [
                        {
                            "name": "core",
                            "ssh_authorized_keys": self.__cluster_configuration.ssh_keys,
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
                        # Disable SELinux, since it breaks Pod volumes
                        file_from_content(
                            "/etc/selinux/config",
                            content_from_lines(
                                "SELINUX=permissive", "SELINUXTYPE=targeted"
                            ),
                        ),
                        # Kubernetes Kubelet
                        file_from_url(
                            "/opt/kubernetes/bin/kubelet",
                            url=yarl.URL(
                                f"https://storage.googleapis.com/kubernetes-release/release/v{self.__cluster_configuration.kubernetes_version}/bin/linux/amd64/kubelet"
                            ),
                            mode=0o755,
                        ),
                        file_from_content(
                            "/etc/kubernetes/kubelet.yaml",
                            yaml.dump(UniversalFCCProvider.kubelet_configuration()),
                            mode=0o600,
                        ),
                    ],
                },
                "systemd": {
                    "units": [
                        {
                            "name": "kubelet.service",
                            "enabled": True,
                            "contents": content_from_repository(
                                "systemd/kubelet.service"
                            ),
                        }
                    ]
                },
            }
        )

    def generate_etcd_configuration(self) -> dict:
        return kx.utility.merge_complex_dictionaries(
            self.__generate_base_configuration(),
            {
                "storage": {
                    "files": [
                        file_from_content(
                            path="/etc/profile.d/node_role.sh",
                            contents=content_from_lines("NODE_ROLE=etcd"),
                        )
                    ]
                }
            },
        )

    def generate_master_configuration(self) -> dict:
        return kx.utility.merge_complex_dictionaries(
            self.__generate_base_configuration(),
            {
                "storage": {
                    "files": [
                        file_from_content(
                            path="/etc/profile.d/node_role.sh",
                            contents=content_from_lines("NODE_ROLE=master"),
                        )
                    ]
                }
            },
        )

    def generate_worker_configuration(self, *, pool_name: str) -> dict:
        return kx.utility.merge_complex_dictionaries(
            self.__generate_base_configuration(),
            {
                "storage": {
                    "files": [
                        file_from_content(
                            path="/etc/profile.d/node_role.sh",
                            contents=content_from_lines("NODE_ROLE=worker"),
                        )
                    ]
                }
            },
        )


class UnstableFCCProvider(FedoraCoreOSConfigurationProvider):
    def __init__(
        self, *, tls_pki_catalog: kx.tls.pki.PublicKeyInfrastructureCatalog,
    ):
        pass

    def generate_etcd_configuration(self) -> dict:
        raise NotImplementedError

    def generate_master_configuration(self) -> dict:
        raise NotImplementedError

    def generate_worker_configuration(self, *, pool_name: str) -> dict:
        raise NotImplementedError
