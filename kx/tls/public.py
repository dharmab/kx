#!/usr/bin/env python3

import cryptography.x509
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
    encryption_key: str


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
    cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
) -> KubernetesPublicKeyInfrastructure:
    certificate_authority_name = kx.tls.crypto.generate_subject_name(
        "kx", organization="kx"
    )
    signing_key = kx.tls.crypto.generate_private_key()
    certificate_authority = kx.tls.crypto.Keypair(
        private_key=signing_key,
        public_key=kx.tls.crypto.generate_certificate_authority_certificate(
            certificate_authority_name, signing_key=signing_key
        ),
    )

    apiserver_alternative_name: cryptography.x509.GeneralNames = [
        # Localhost for master node loop traffic
        cryptography.x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        # Well-known IP for apiserver Kubernetes service
        cryptography.x509.IPAddress(ipaddress.ip_address("192.168.0.1")),
        # CoreDNS names for apiserver
        cryptography.x509.DNSName("kubernetes"),
        cryptography.x509.DNSName("kubernetes.default"),
        cryptography.x509.DNSName("kubernetes.default.svc"),
        cryptography.x509.DNSName("kubernetes.default.svc.cluster"),
        cryptography.x509.DNSName("kubernetes.default.svc.cluster.local"),
    ]
    for name in apiserver_names:
        if isinstance(name, yarl.URL):
            apiserver_alternative_name.append(
                cryptography.x509.DNSName(name.human_repr())
            )
        else:
            apiserver_alternative_name.append(cryptography.x509.IPAddress(name))

    apiserver_keypair = kx.tls.crypto.generate_keypair(
        kx.tls.crypto.generate_subject_name(
            "kube-apiserver", organization="system:kubelet-api-admin"
        ),
        subject_alternative_name=apiserver_alternative_name,
        key_usage=kx.tls.crypto.standard_key_usage(),
        certificate_authority_keypair=certificate_authority,
    )
    # https://kubernetes.io/docs/reference/access-authn-authz/rbac/#core-component-roles
    controller_manager = kx.tls.crypto.generate_keypair(
        kx.tls.crypto.generate_subject_name(
            "kube-scheduler", organization="system:kube-scheduler"
        ),
        subject_alternative_name=apiserver_alternative_name,
        key_usage=kx.tls.crypto.standard_key_usage(),
        certificate_authority_keypair=certificate_authority,
    )
    scheduler_keypair = kx.tls.crypto.generate_keypair(
        kx.tls.crypto.generate_subject_name(
            "kube-scheduler", organization="system:kube-scheduler"
        ),
        subject_alternative_name=apiserver_alternative_name,
        key_usage=kx.tls.crypto.standard_key_usage(),
        certificate_authority=certificate_authority,
    )
