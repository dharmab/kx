#!/usr/bin/env python3

import dataclasses
import ipaddress
import kx.configuration.cluster
import kx.tls.crypto
import typing
import yarl


@dataclasses.dataclass
class Keypair:
    public_key: str
    private_key: str


@dataclasses.dataclass
class KubernetesPublicKeyInfrastructure:
    certificate_authority: Keypair
    apiserver_keypair: Keypair
    controller_manager_keypair: Keypair
    scheduler_keypair: Keypair
    encrypion_key: str


@dataclasses.dataclass
class EtcdPublicKeyInfrastructure:
    certificate_authority: Keypair
    etcd_server_keypair: Keypair
    etcd_peer_keypair: Keypair
    etcd_apiserver_client_keypair: Keypair
    etcd_metrics_client_keypair: Keypair


def create_kubernetes_pki(
    *,
    apiserver_names: typing.List[
        typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address, yarl.URL]
    ],
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration
) -> KubernetesPublicKeyInfrastructure:
    pass
