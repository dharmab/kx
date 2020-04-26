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
                        # Bootstrap the cluster using static discovery (using
                        # static IP addresses known ahead of time).
                        # https://etcd.io/docs/v3.4.0/op-guide/clustering/#static
                        "--name=$(NODE_NAME)",
                        "--initial-advertise-peer-urls=https://$(HOST_IP):2380",
                        "--listen-peer-urls=https://$(HOST_IP):2380",
                        "--listen-client-urls=https://$(HOST_IP):2379",
                        "--advertise-client-urls=https://$(HOST_IP):2379",
                        # Note that all --initial-cluster* flags are only used
                        # on first run and are ignored if the data directory
                        # has previously been initialized.
                        "--initial-cluster",
                        ",".join(
                            f"{k}=https://{v}:2380" for k, v in etcd_peers.items()
                        ),
                        "--initial-cluster-state="
                        + ("existing" if is_existing_cluster else "new"),
                        f"--initial-cluster-token={cluster_configuration.etcd_token}",
                        # Configure client/server and peer TLS.
                        # https://etcd.io/docs/v3.4.0/op-guide/security/
                        "--cert-file=/etc/etcd/tls/etcd_server.pem",
                        "--key-file=/etc/etcd/tls/etcd_server.key",
                        "--trusted-ca-file=/etc/etcd/tls/etcd_ca.pem",
                        "--peer-cert-file=/etc/etcd/tls/etcd_peer.pem",
                        "--peer-key-file=/etc/etcd/tls/etcd_peer.key",
                        "--peer-client-cert-auth=True",
                        "--peer-trusted-ca-file=/etc/etcd/tls/etcd_ca.pem",
                        # Store the DB and WAL files in /var/lib/.
                        "--data-dir=/var/lib/etcd/data",
                        # Set the DB size quota to maximum allowed size of 8GB.
                        "--quota-backend-bytes=" + str(8 * 1024 ** 3),
                        # Set a soft limit on the number of WAL files and
                        # reduce the number of snapshots from the 3.2+ defaults
                        # to encourage aggressive WAL file clean up and
                        # mitigate excessive disk usage.
                        # https://github.com/etcd-io/etcd/blob/master/Documentation/op-guide/maintenance.md#raft-log-retention
                        # https://github.com/etcd-io/etcd/issues/8472#issuecomment-345882702
                        # https://github.com/etcd-io/etcd/issues/10885#issuecomment-512613088
                        "--max-wals=5",
                        "--snapshot-count=10000",
                        # Enable periodic auto-compaction to aggressively
                        # compact the DB file and prevent excessive disk usage.
                        # The Kubernetes apiserver also triggers compaction
                        # every 5 minutes, but this is a good safety net in
                        # case the apiserver goes down.
                        # https://github.com/etcd-io/etcd/blob/master/Documentation/op-guide/maintenance.md#auto-compaction
                        "--auto-compaction-retention=5m",
                        # Use the new structured log format introduced in 3.4
                        # instead of the deprecated default. The structured
                        # logs are less readable in their raw form but easier
                        # to parse (e.g. in ELK or Splunk).
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
