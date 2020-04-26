#!/usr/bin/env python3

import abc
import ipaddress
import jinja2
import json
import kx.configuration
import kx.kubernetes.static_pods
import kx.tls.pki
import kx.utility
import typing
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
        self,
        *,
        cluster_configuration: kx.configuration.ClusterConfiguration,
        etcd_peers: typing.Dict[
            str, typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
        ],
    ):
        self.__cluster_configuration = cluster_configuration
        self.__etcd_peers = etcd_peers

    @staticmethod
    def kubelet_configuration() -> dict:
        # https://kubernetes.io/docs/tasks/administer-cluster/kubelet-config-file/
        # https://github.com/kubernetes/kubernetes/blob/master/staging/src/k8s.io/kubelet/config/v1beta1/types.go
        return {
            "apiVersion": "kubelet.config.k8s.io/v1beta1",
            "kind": "KubeletConfiguration",
            "authentication": {
                "anonymous": {"enabled": True},
                # TODO use webhook mode after bootstrapping TLS PKI
                "webhook": {"enabled": False},
            },
            "authorization": {"mode": "AlwaysAllow"},
            # Match Kubelet's cgroup to Docker's (which is systemd for reasons
            # described in docker.service)
            "cgroupDriver": "systemd",
            "staticPodPath": "/etc/kubernetes/pods/",
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
                        {"path": "/etc/kubernetes/pods"},
                        {"path": "/etc/kubernetes/tls"},
                        {"path": "/opt/kubernetes/bin"},
                        {"path": "/opt/kx/bin"},
                    ],
                    "files": [
                        file_from_content(
                            path="/etc/profile.d/cloud_provider.sh",
                            contents=content_from_lines(
                                f"CLOUD_PROVIDER={self.__cluster_configuration.provider}"
                            ),
                        ),
                        # Disable SELinux, since it breaks Pod volumes
                        file_from_content(
                            "/etc/selinux/config",
                            content_from_lines(
                                "SELINUX=disabled", "SELINUXTYPE=targeted"
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
                        file_from_url(
                            "/opt/cni/bin/cni-plugins.tar.gz",
                            url=yarl.URL(
                                f"https://github.com/containernetworking/plugins/releases/download/v0.8.5/cni-plugins-linux-amd64-v{self.__cluster_configuration.cni_plugins_version}.tgz"
                            ),
                            mode=0o755,
                        ),
                        file_from_content(
                            "/opt/kx/bin/kubelet-wrapper",
                            contents=content_from_repository(
                                "files/scripts/kubelet-wrapper.sh"
                            ),
                            mode=0o744,
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
                        ),
                        file_from_content(
                            path="/etc/kubernetes/pods/etcd.yaml",
                            contents=yaml.dump(
                                kx.kubernetes.static_pods.etcd(
                                    cluster_configuration=self.__cluster_configuration,
                                    etcd_peers=self.__etcd_peers,
                                    is_existing_cluster=False,
                                )
                            ),
                        ),
                    ],
                    "directories": [{"path": "/var/lib/etcd/data"}],
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
        self,
        *,
        kubernetes_pki: kx.tls.pki.KubernetesPublicKeyInfrastructure,
        etcd_pki: kx.tls.pki.EtcdPublicKeyInfrastructure,
    ):
        self.__kubernetes_pki = kubernetes_pki
        self.__etcd_pki = etcd_pki

    def __generate_base_configuration(self) -> dict:
        return {
            "storage": {
                "files": [
                    file_from_content(
                        "/etc/kubernetes/tls/kubernetes_ca.pem",
                        contents=self.__kubernetes_pki.certificate_authority.public_key,
                    ),
                ]
            }
        }

    def generate_etcd_configuration(self) -> dict:
        return kx.utility.merge_complex_dictionaries(
            {
                "storage": {
                    "files": [
                        file_from_content(
                            "/etc/etcd/tls/etcd_ca.pem",
                            contents=self.__etcd_pki.certificate_authority.public_key,
                        ),
                        file_from_content(
                            "/etc/etcd/tls/etcd_peer.key",
                            contents=self.__etcd_pki.etcd_peer_keypair.private_key,
                            mode=0o600,
                        ),
                        file_from_content(
                            "/etc/etcd/tls/etcd_peer.pem",
                            contents=self.__etcd_pki.etcd_peer_keypair.public_key,
                        ),
                        file_from_content(
                            "/etc/etcd/tls/etcd_server.key",
                            contents=self.__etcd_pki.etcd_server_keypair.private_key,
                            mode=0o600,
                        ),
                        file_from_content(
                            "/etc/etcd/tls/etcd_server.pem",
                            contents=self.__etcd_pki.etcd_server_keypair.public_key,
                        ),
                    ]
                }
            },
        )

    def generate_master_configuration(self) -> dict:
        return kx.utility.merge_complex_dictionaries(
            {
                "storage": {
                    "files": [
                        file_from_content(
                            "/etc/etcd/tls/etcd_ca.pem",
                            contents=self.__etcd_pki.certificate_authority.public_key,
                        ),
                        file_from_content(
                            "/etc/etcd/tls/kube_apiserver.key",
                            contents=self.__etcd_pki.etcd_apiserver_client_keypair.private_key,
                            mode=0o600,
                        ),
                        file_from_content(
                            "/etc/etcd/tls/kube_apiserver.pem",
                            contents=self.__etcd_pki.etcd_apiserver_client_keypair.public_key,
                        ),
                        file_from_content(
                            "/etc/kubernetes/tls/kube_apiserver.key",
                            contents=self.__kubernetes_pki.apiserver_keypair.private_key,
                            mode=0o600,
                        ),
                        file_from_content(
                            "/etc/kubernetes/tls/kube_apiserver.pem",
                            contents=self.__kubernetes_pki.apiserver_keypair.public_key,
                        ),
                        file_from_content(
                            "/etc/kubernetes/tls/kube_scheduler.key",
                            contents=self.__kubernetes_pki.scheduler_keypair.private_key,
                            mode=0o600,
                        ),
                        file_from_content(
                            "/etc/kubernetes/tls/kube_scheduler.pem",
                            contents=self.__kubernetes_pki.scheduler_keypair.public_key,
                        ),
                        file_from_content(
                            "/etc/kubernetes/tls/kube_controller_manager.key",
                            contents=self.__kubernetes_pki.controller_manager_keypair.private_key,
                            mode=0o600,
                        ),
                        file_from_content(
                            "/etc/kubernetes/tls/kube_controller_manager.pem",
                            contents=self.__kubernetes_pki.controller_manager_keypair.public_key,
                        ),
                    ]
                }
            },
        )

    def generate_worker_configuration(self, *, pool_name: str) -> dict:
        return {}
