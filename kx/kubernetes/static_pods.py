#!/usr/bin/env python3

import ipaddress
import kx.configuration
import typing


def etcd(
    cluster_configuration: kx.configuration.ClusterConfiguration,
    etcd_peers: typing.Dict[
        str, typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    ],
    is_existing_cluster: bool,
) -> dict:
    peer_urls = [f"{k}=https://{v}:2380" for k, v in etcd_peers.items()]
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "etcd",
            "namespace": "kube-system",
            "labels": {"static": "true", "app": "etcd"},
        },
        "spec": {
            "containers": [
                {
                    "name": "etcd",
                    "image": f"gcr.io/etcd-development/etcd:v{cluster_configuration.etcd_version}",
                    "command": [
                        "etcd",
                        # https://etcd.io/docs/v3.4.0/op-guide/clustering/#static
                        "--name=$(NODE_NAME)",
                        "--initial-advertise-peer-urls",
                        ",".join(peer_urls),
                        "--listen-peer-urls=https://$(HOST_IP):2380",
                        "--advertise-client-urls=https://$(HOST_IP):2379",
                        "--listen-client-urls=https://$(HOST_IP):2379",
                        # Note that --initial-cluster options are only used on
                        # first run and ignored on subsequent runs
                        "--initial-cluster",
                        "--initial-cluster-state="
                        + ("existing" if is_existing_cluster else "new"),
                        f"--initial-cluster-token={cluster_configuration.etcd_token}",
                        # https://etcd.io/docs/v3.4.0/op-guide/security/
                        "--cert-file=/etc/etcd/tls/etcd_server.pem",
                        "--key-file=/etc/etcd/tls/etcd_server.key",
                        "--trusted-ca-file=/etc/etcd/tls/etcd_ca.pem",
                        "--peer-cert-file=/etc/etcd/tls/etcd_peer.pem",
                        "--peer-key-file=/etc/etcd/tls/etcd_peer.key",
                        "--peer-client-cert-auth=True",
                        "--peer-trusted-ca-file=/etc/etcd/tls/etcd_ca.pem",
                        "--data-dir=/var/lib/etcd/data",
                        # Set quota to maximum allowed size of 8GB
                        "--quota-backend-bytes=" + str(8 * 1024 ** 3),
                        # Enable periodic auto-compaction
                        "--auto-compaction-retention=5m",
                        "--logger=zap",
                    ],
                    "env": [
                        {
                            "name": "NODE_NAME",
                            "valueFrom": {"fieldRef": {"fieldPath": "spec.nodeName"}},
                        },
                        {
                            "name": "HOST_IP",
                            "valueFrom": {"fieldRef": {"fieldPath": "status.hostIP"}},
                        },
                    ],
                    "ports": [
                        {
                            "name": "peer",
                            "containerPort": 2379,
                            "protocol": "TCP",
                            "hostPort": 2379,
                        },
                        {
                            "name": "server",
                            "containerPort": 2380,
                            "protocol": "TCP",
                            "hostPort": 2380,
                        },
                    ],
                    "volumeMounts": [
                        {"name": "etcd-data-dir", "mountPath": "/var/lib/etcd/data"},
                        {"name": "etcd-tls-dir", "mountPath": "/etc/etcd/tls"},
                    ],
                }
            ],
            "hostNetwork": True,
            "volumes": [
                {"name": "etcd-data-dir", "hostPath": {"path": "/var/lib/etcd/data"}},
                {"name": "etcd-tls-dir", "hostPath": {"path": "/etc/etcd/tls"}},
            ],
        },
    }
