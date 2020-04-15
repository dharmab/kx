#!/usr/bin/env python3
#
# This module contains functions and types

import cryptography.x509
import dataclasses
import ipaddress
import kx.configuration.cluster
import kx.tls.crypto
import typing
import yarl


@dataclasses.dataclass
class KubernetesPublicKeyInfrastructure:
    certificate_authority: kx.tls.crypto.SerializedKeypair
    apiserver_keypair: kx.tls.crypto.SerializedKeypair
    controller_manager_keypair: kx.tls.crypto.SerializedKeypair
    scheduler_keypair: kx.tls.crypto.SerializedKeypair


def create_kubernetes_pki(
    *,
    apiserver_names: typing.List[
        typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address, yarl.URL]
    ],
    encryption_key: str
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
    controller_manager_keypair = kx.tls.crypto.generate_keypair(
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
        certificate_authority_keypair=certificate_authority,
    )

    return KubernetesPublicKeyInfrastructure(
        certificate_authority=kx.tls.crypto.serialize_keypair(
            certificate_authority, encryption_key=encryption_key
        ),
        apiserver_keypair=kx.tls.crypto.serialize_keypair(
            apiserver_keypair, encryption_key=encryption_key
        ),
        scheduler_keypair=kx.tls.crypto.serialize_keypair(
            scheduler_keypair, encryption_key=encryption_key
        ),
        controller_manager_keypair=kx.tls.crypto.serialize_keypair(
            controller_manager_keypair, encryption_key=encryption_key
        ),
    )


@dataclasses.dataclass
class EtcdPublicKeyInfrastructure:
    certificate_authority: kx.tls.crypto.SerializedKeypair
    etcd_server_keypair: kx.tls.crypto.SerializedKeypair
    etcd_peer_keypair: kx.tls.crypto.SerializedKeypair
    etcd_apiserver_client_keypair: kx.tls.crypto.SerializedKeypair


def create_etcd_pki(
    *,
    etcd_peer_ip_addresses: typing.List[
        typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    ],
    etcd_server_ip_addresses: typing.List[
        typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    ],
    encryption_key: str
) -> EtcdPublicKeyInfrastructure:
    certificate_authority_name = kx.tls.crypto.generate_subject_name(
        "etcd", organization="kx"
    )
    signing_key = kx.tls.crypto.generate_private_key()
    certificate_authority = kx.tls.crypto.Keypair(
        private_key=signing_key,
        public_key=kx.tls.crypto.generate_certificate_authority_certificate(
            certificate_authority_name, signing_key=signing_key
        ),
    )

    etcd_peer_keypair = kx.tls.crypto.generate_keypair(
        kx.tls.crypto.generate_subject_name("etcd-peer", organization="etcd-peers"),
        subject_alternative_name=cryptography.x509.SubjectAlternativeName(
            [cryptography.x509.IPAddress(ip) for ip in etcd_peer_ip_addresses]
        ),
        key_usage=kx.tls.crypto.standard_key_usage(),
        certificate_authority_keypair=certificate_authority,
    )

    etcd_server_keypair = kx.tls.crypto.generate_keypair(
        kx.tls.crypto.generate_subject_name("etcd", organization="etcd-servers"),
        subject_alternative_name=cryptography.x509.SubjectAlternativeName(
            [
                cryptography.x509.IPAddress(ip)
                for ip in etcd_server_ip_addresses
                + [ipaddress.IPv4Address("127.0.0.1")]
            ]
        ),
        key_usage=kx.tls.crypto.standard_key_usage(),
        certificate_authority_keypair=certificate_authority,
    )

    apiserver_keypair = kx.tls.crypto.generate_keypair(
        kx.tls.crypto.generate_subject_name(
            "kube-apiserver", organization="etcd-rw-clients"
        ),
        subject_alternative_name=None,
        key_usage=kx.tls.crypto.standard_key_usage(),
        certificate_authority_keypair=certificate_authority,
    )

    return EtcdPublicKeyInfrastructure(
        certificate_authority=kx.tls.crypto.serialize_keypair(
            certificate_authority, encryption_key=encryption_key
        ),
        etcd_peer_keypair=kx.tls.crypto.serialize_keypair(
            etcd_peer_keypair, encryption_key=encryption_key
        ),
        etcd_server_keypair=kx.tls.crypto.serialize_keypair(
            etcd_server_keypair, encryption_key=encryption_key
        ),
        etcd_apiserver_client_keypair=kx.tls.crypto.serialize_keypair(
            apiserver_keypair, encryption_key=encryption_key
        ),
    )


@dataclasses.dataclass
class PublicKeyInfrastructureCatalog:
    kubernetes_signing_key: yarl.URL
    kubernetes_certificate_authority: yarl.URL
    apiserver_certificate: yarl.URL
    apiserver_private_key: yarl.URL
    controller_manager_certificate: yarl.URL
    controller_manager_private_key: yarl.URL
    scheduler_certificate: yarl.URL
    scheduler_private_key: yarl.URL
    etcd_certificate_authority: yarl.URL
    etcd_peer_certificate: yarl.URL
    etcd_peer_private_key: yarl.URL
    etcd_server_certificate: yarl.URL
    etcd_server_private_key: yarl.URL
    etcd_apiserver_client_certificate: yarl.URL
    etcd_apiserver_client_private_key: yarl.URL
